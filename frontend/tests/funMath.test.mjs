import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { parse, compileScript, compileTemplate } from "@vue/compiler-sfc";
import {
  canStartMathQuestion, currentMathQuestion, isMathQuestionFinished, mathClockAnchor,
  mathCountdownLabel, mathQuestionLabel, mathSecondsRemaining, mathServerTime, validMathAnswer,
} from "../src/app/funMathState.js";
import { parseRoute } from "../src/app/router.js";
import { routeApiPaths } from "../src/app/routeApiPaths.js";
import { routeTitle } from "../src/app/routeTitles.js";
import { buildSidebarNavItems } from "../src/app/sidebarNav.js";
import { coreRouteLoaders } from "../src/app/routeLoaders/coreRouteLoaders.js";
import { moduleForRoute } from "../src/app/pageVersion.js";

const source = readFileSync(new URL("../src/app/pages/FunMathPage.vue", import.meta.url), "utf8");
const pending = { id: 1, status: "pending" };
const active = { id: 2, status: "active", deadlineAt: "2026-10-28T08:10:00Z" };
const completed = { id: 1, status: "correct", left: 123, right: 456, answer: 56088, reward: 100 };

test("fun math has a route, title, version key and navigation entry", () => {
  const route = parseRoute("/fun-math", "");
  assert.equal(route.name, "funMath");
  assert.equal(routeTitle(route), "趣味数学");
  assert.equal(moduleForRoute(route).key, "fun-math");
  const item = buildSidebarNavItems({ route, shell: {} }).find((entry) => entry.path === "/fun-math");
  assert.equal(item.label, "趣味数学");
  assert.equal(item.active, true);
  assert.equal(routeApiPaths.funMathStart(), "/api/vue/fun-math/start");
  assert.equal(routeApiPaths.funMathAnswer(), "/api/vue/fun-math/answer");
});

test("fun math initial loader never reads cached progress", async () => {
  const originalFetch = globalThis.fetch;
  let requested;
  globalThis.fetch = async (url, options) => {
    requested = { url, options };
    return new Response(JSON.stringify({ day: "2026-10-28", questions: [] }), { headers: { "content-type": "application/json" } });
  };
  try {
    const data = { value: null };
    await coreRouteLoaders.funMath({ data });
    assert.equal(requested.url, "/api/vue/fun-math");
    assert.equal(requested.options.cache, "no-store");
    assert.equal(data.value.day, "2026-10-28");
  } finally { globalThis.fetch = originalFetch; }
});

test("countdown uses anchored server time and monotonic elapsed time", () => {
  const anchor = mathClockAnchor("2026-10-28T08:00:00Z", 1000);
  assert.equal(mathSecondsRemaining(active, mathServerTime(anchor, 1000)), 600);
  assert.equal(mathSecondsRemaining(active, mathServerTime(anchor, 61000)), 540);
  assert.equal(mathSecondsRemaining(active, mathServerTime(anchor, 601000)), 0);
  assert.equal(mathSecondsRemaining(active, mathServerTime(anchor, 999000)), 0);
  assert.equal(mathSecondsRemaining(pending, mathServerTime(anchor, 1000)), 0);
});

test("reload anchors at current server time rather than restarting ten minutes", () => {
  const anchor = mathClockAnchor("2026-10-28T08:09:59.500Z", 17);
  assert.equal(mathSecondsRemaining(active, mathServerTime(anchor, 17)), 1);
  assert.equal(mathSecondsRemaining(active, mathServerTime(anchor, 517)), 0);
  assert.equal(mathCountdownLabel(600), "10:00");
  assert.equal(mathCountdownLabel(1), "00:01");
  assert.equal(mathCountdownLabel(-2), "00:00");
});

test("invalid time cannot enable a client timer", () => {
  assert.equal(mathServerTime(mathClockAnchor("invalid", 1), 10), null);
  assert.equal(mathSecondsRemaining(active, null), 0);
  assert.equal(mathSecondsRemaining({ ...active, deadlineAt: "invalid" }, Date.now()), 0);
});

test("numeric keyboard input is validated but correctness is not decided locally", () => {
  for (const value of ["10000", "998001", " 56088 ", "0"]) assert.equal(validMathAnswer(value), true);
  for (const value of ["", "1e5", "1.5", "-1", "12a", "1234567", true, null]) assert.equal(validMathAnswer(value), false);
  assert.doesNotMatch(source, /question\.value\.left\s*\*\s*question\.value\.right/);
  assert.doesNotMatch(source, /earnedEnergy\s*\+\s*100/);
});

test("only the next pending question can be started and finished questions stay final", () => {
  assert.equal(canStartMathQuestion({ nextQuestionId: 1 }, pending), true);
  assert.equal(canStartMathQuestion({ nextQuestionId: 2 }, pending), false);
  assert.equal(canStartMathQuestion({ nextQuestionId: 1, activeQuestionId: 2 }, pending), false);
  for (const status of ["correct", "incorrect", "expired"]) {
    assert.equal(isMathQuestionFinished({ status }), true);
    assert.equal(canStartMathQuestion({ nextQuestionId: 1 }, { id: 1, status }), false);
  }
  assert.equal(isMathQuestionFinished(active), false);
});

test("active questions remain current while finished questions can be reviewed", () => {
  const payload = { activeQuestionId: 2, nextQuestionId: 3, questions: [completed, active, { id: 3, status: "pending" }] };
  assert.equal(currentMathQuestion(payload).id, 2);
  assert.equal(currentMathQuestion(payload, 1).id, 1);
  assert.equal(mathQuestionLabel(active), "作答中");
  assert.equal(mathQuestionLabel({ status: "expired" }), "已超时");
});

test("page serializes mutations, rejects stale responses and cleans up requests", () => {
  assert.match(source, /if \(busy\.value \|\| disposed\) return/);
  assert.match(source, /sequence !== requestSequence/);
  assert.match(source, /currentController\?\.abort\(\)/);
  assert.match(source, /window\.clearInterval\(ticker\)/);
  assert.match(source, /visibilitychange/);
  assert.match(source, /cache: "no-store"/);
  assert.match(source, /questionId: question\.value\.id, answer: answer\.value\.trim\(\)/);
  assert.match(source, /secondsLeft\.value > 0/);
  assert.match(source, /controller\.abort\(\), 20000/);
});

test("pending questions do not render operands and inputs remain usable on mobile", () => {
  assert.match(source, /v-if="question\.status === 'pending'"/);
  assert.match(source, /inputmode="numeric"/);
  assert.match(source, /autocomplete="off"/);
  assert.doesNotMatch(source, /isMobileDisplay|readonly/);
  assert.match(source, /以服务器收到答案的时间和判定为准/);
  assert.match(source, /跨天未完成的题目会结束/);
});

test("Vue script and template compile without warnings or errors", () => {
  const { descriptor, errors } = parse(source, { filename: "FunMathPage.vue" });
  assert.deepEqual(errors, []);
  const script = compileScript(descriptor, { id: "fun-math-test" });
  assert.ok(script.content.includes("requestState"));
  const compiled = compileTemplate({ source: descriptor.template.content, filename: "FunMathPage.vue", id: "fun-math-test", compilerOptions: { bindingMetadata: script.bindings } });
  assert.deepEqual(compiled.errors, []);
});
