import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  canUsePhoneticForAi,
  createWordEditSnapshot,
  formatPhonetic,
  isWebsterRespelling,
  normalizePhonetic,
} from "../src/app/wordEditingActions.js";

test("ordinary IPA keeps its existing single-slash display and editable value", () => {
  for (const value of ["wɜːd", "/wɜːd/", " //wɜːd// "]) {
    assert.equal(formatPhonetic(value), "/wɜːd/");
    assert.equal(normalizePhonetic(value), "wɜːd");
    assert.equal(isWebsterRespelling(value), false);
    assert.equal(canUsePhoneticForAi(value), true);
  }
});

test("Webster respelling retains attribution without IPA slashes, including editing", () => {
  const value = "韦氏标音：ˈlȯn-dər";
  for (const stored of [value, ` ${value} `, `/${value}/`]) {
    assert.equal(formatPhonetic(stored), value);
    assert.equal(createWordEditSnapshot({ phonetic: stored }).phonetic, value);
    assert.equal(isWebsterRespelling(stored), true);
    assert.equal(canUsePhoneticForAi(stored), false);
  }
  assert.equal(canUsePhoneticForAi("韦氏标音: ˈlȯn-dər"), false);
});

test("empty phonetics stay empty and cannot be sent to IPA audio generation", () => {
  for (const value of [null, undefined, "", " / / "]) {
    assert.equal(formatPhonetic(value), "");
    assert.equal(canUsePhoneticForAi(value), false);
  }
});

test("title and audio manager share display formatting and guard non-IPA audio", () => {
  const title = readFileSync(new URL("../src/app/components/WordDetailTitleStack.vue", import.meta.url), "utf8");
  const audio = readFileSync(new URL("../src/app/components/WordAudioManagerModal.vue", import.meta.url), "utf8");
  assert.match(title, /formatPhonetic\(phoneticText\)/);
  assert.match(audio, /textMode !== "phonetic" \|\| canUsePhoneticForAi\(phoneticText\.value\)/);
  assert.match(audio, /非 IPA/);
  assert.match(audio, /formatPhonetic\(phoneticText\.value\)/);
});
