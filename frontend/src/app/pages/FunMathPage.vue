<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Calculator, Cat, Check, Clock3, RefreshCw, Sparkles, Trophy } from "lucide-vue-next";
import { fetchJson } from "../utils.js";
import { routeApiPaths } from "../routeApiPaths.js";
import {
  canStartMathQuestion, currentMathQuestion, isMathQuestionFinished,
  mathClockAnchor, mathCountdownLabel, mathQuestionLabel, mathSecondsRemaining,
  mathServerTime, validMathAnswer,
} from "../funMathState.js";

const props = defineProps({ data: { type: Object, required: true }, go: { type: Function, required: true } });
const payload = ref({});
const selectedId = ref(null);
const answer = ref("");
const answerInput = ref(null);
const busy = ref("");
const error = ref("");
const notice = ref("");
const monotonicNow = ref(performance.now());
const clock = ref(mathClockAnchor(null, monotonicNow.value));
let requestSequence = 0;
let disposed = false;
let ticker;
let currentController;
let lastSyncAttempt = -Infinity;

const questions = computed(() => payload.value.questions || []);
const question = computed(() => currentMathQuestion(payload.value, selectedId.value));
const activeQuestion = computed(() => questions.value.find((item) => item.id === payload.value.activeQuestionId));
const serverTime = computed(() => mathServerTime(clock.value, monotonicNow.value));
const secondsLeft = computed(() => mathSecondsRemaining(activeQuestion.value, serverTime.value));
const finished = computed(() => isMathQuestionFinished(question.value));
const canStart = computed(() => canStartMathQuestion(payload.value, question.value));
const canSubmit = computed(() => question.value?.status === "active" && secondsLeft.value > 0 && validMathAnswer(answer.value) && !busy.value);
const allDone = computed(() => Number(payload.value.completed || 0) >= Number(payload.value.total || 5));
const progress = computed(() => `${Math.min(100, Number(payload.value.completed || 0) / Number(payload.value.total || 5) * 100)}%`);

function applyPayload(value, preferredId = null) {
  if (!value || !Array.isArray(value.questions) || !value.day || !Number.isFinite(Date.parse(value.serverNow))) {
    throw new Error("题目状态加载失败，请同步后重试。");
  }
  const oldDay = payload.value.day;
  const oldQuestionId = question.value?.id;
  payload.value = value;
  monotonicNow.value = performance.now();
  clock.value = mathClockAnchor(value.serverNow, monotonicNow.value);
  if (oldDay !== value.day) {
    selectedId.value = value.activeQuestionId || value.nextQuestionId || null;
    answer.value = "";
    if (oldDay) notice.value = "新的一天开始了，今天的 5 道题已准备好。";
  } else if (preferredId != null) {
    selectedId.value = preferredId;
  }
  if (oldQuestionId !== question.value?.id || question.value?.status !== "active") answer.value = "";
}

watch(() => props.data, (value) => {
  requestSequence += 1;
  busy.value = "";
  try { applyPayload(value); } catch (failure) { error.value = failure.message; }
}, { immediate: true });

async function requestState(action = "sync", requestBody = null) {
  if (busy.value || disposed) return;
  const sequence = ++requestSequence;
  busy.value = action;
  error.value = "";
  if (action !== "sync") notice.value = "";
  lastSyncAttempt = performance.now();
  const controller = new AbortController();
  currentController = controller;
  const timeout = window.setTimeout(() => controller.abort(), 20000);
  try {
    const endpoint = action === "start" ? routeApiPaths.funMathStart()
      : action === "answer" ? routeApiPaths.funMathAnswer() : routeApiPaths.funMath();
    const options = action === "sync"
      ? { skipCache: true, cache: "no-store" }
      : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(requestBody) };
    const value = await fetchJson(endpoint, { ...options, signal: controller.signal });
    if (disposed || sequence !== requestSequence) return;
    applyPayload(value, requestBody?.questionId);
    if (value.result?.message) notice.value = value.result.message;
    if (action === "start") {
      await nextTick();
      if (!disposed && sequence === requestSequence) answerInput.value?.focus();
    }
  } catch (failure) {
    if (!disposed && sequence === requestSequence) {
      const message = failure.name === "AbortError" ? "连接超时，服务器可能已收到请求。" : failure.message || "网络暂时不可用。";
      error.value = `${message} 可点击“同步进度”确认结果，不会重复发奖。`;
    }
  } finally {
    window.clearTimeout(timeout);
    if (currentController === controller) currentController = null;
    if (!disposed && sequence === requestSequence) busy.value = "";
  }
}

function startQuestion() {
  if (!canStart.value || busy.value) return;
  requestState("start", { day: payload.value.day, questionId: question.value.id });
}

function submitAnswer() {
  if (!canSubmit.value || busy.value) return;
  requestState("answer", { day: payload.value.day, questionId: question.value.id, answer: answer.value.trim() });
}

function selectQuestion(item) {
  if (busy.value) return;
  if (item.status === "pending" && item.id !== payload.value.nextQuestionId) return;
  if (item.id !== selectedId.value) answer.value = "";
  selectedId.value = item.id;
  notice.value = "";
}

function nextQuestion() {
  const next = questions.value.find((item) => item.id === (payload.value.activeQuestionId || payload.value.nextQuestionId));
  if (next) selectQuestion(next);
}

function syncOnVisible() {
  if (document.visibilityState === "visible") requestState();
}

function tick() {
  monotonicNow.value = performance.now();
  if (busy.value || document.visibilityState !== "visible") return;
  const rollover = Date.parse(payload.value.nextRefreshAt || "");
  const due = (activeQuestion.value && secondsLeft.value === 0)
    || (Number.isFinite(rollover) && serverTime.value >= rollover);
  const sinceSync = monotonicNow.value - lastSyncAttempt;
  // Reconcile expiry and other tabs with the server; never grant a reward locally.
  if ((due && sinceSync >= 10000) || sinceSync >= 30000) requestState();
}

onMounted(() => {
  ticker = window.setInterval(tick, 250);
  document.addEventListener("visibilitychange", syncOnVisible);
  window.addEventListener("online", syncOnVisible);
  requestState();
});
onBeforeUnmount(() => {
  disposed = true;
  requestSequence += 1;
  currentController?.abort();
  window.clearInterval(ticker);
  document.removeEventListener("visibilitychange", syncOnVisible);
  window.removeEventListener("online", syncOnVisible);
});
</script>

<template>
  <section class="fun-math-page">
    <header class="panel math-hero">
      <div class="math-hero-copy">
        <p class="math-kicker"><Sparkles :size="15" aria-hidden="true" /> DAILY MATH CLUB</p>
        <h1>趣味数学<span class="math-title-dot">.</span></h1>
        <p>动动脑筋，给猫咪攒一点能量。</p>
        <div class="math-hero-tags"><span>三位数 × 三位数</span><span>每日随机 5 题</span></div>
      </div>
      <div class="math-hero-symbol" aria-hidden="true"><Calculator :size="46" /><span>×</span><small>LET'S TRY!</small></div>
    </header>

    <section class="math-stats" aria-label="今日数学进度">
      <div><span>今日题目</span><strong>{{ payload.day || '…' }}</strong><small>北京时间</small></div>
      <div><span>完成进度</span><strong>{{ payload.completed || 0 }} <small>/ {{ payload.total || 5 }}</small></strong><small>已答对 {{ payload.correct || 0 }} 题</small></div>
      <div class="math-energy"><span><Cat :size="15" aria-hidden="true" /> 今日获得</span><strong>+{{ payload.earnedEnergy || 0 }}</strong><small>猫咪能量 · 每日最多 500</small></div>
    </section>

    <section class="panel math-workspace" aria-labelledby="math-question-title">
      <div class="math-progress-track" role="progressbar" aria-label="今日完成进度" :aria-valuenow="payload.completed || 0" :aria-valuemax="payload.total || 5" aria-valuemin="0"><span :style="{ width: progress }"></span></div>
      <div class="math-workspace-toolbar">
        <strong>今天的小挑战</strong>
        <button class="math-sync-button" type="button" :disabled="!!busy" @click="requestState()"><RefreshCw :size="14" aria-hidden="true" />{{ busy === 'sync' ? '同步中…' : '同步进度' }}</button>
      </div>
      <nav class="math-question-steps" aria-label="每日五道题">
        <button v-for="item in questions" :key="item.id" type="button" :class="[item.status, { selected: question?.id === item.id }]" :disabled="!!busy || (item.status === 'pending' && item.id !== payload.nextQuestionId)" :aria-current="question?.id === item.id ? 'step' : undefined" @click="selectQuestion(item)">
          <span class="math-step-number"><Check v-if="item.status === 'correct'" :size="18" aria-hidden="true" /><template v-else>{{ item.id }}</template></span>
          <small>{{ mathQuestionLabel(item) }}</small>
        </button>
      </nav>

      <p v-if="error" class="math-error" role="alert">{{ error }}</p>
      <p v-if="notice" class="math-notice" role="status">{{ notice }}</p>
      <div v-if="activeQuestion && question?.id !== activeQuestion.id" class="math-active-notice" role="status">第 {{ activeQuestion.id }} 题仍在计时：{{ mathCountdownLabel(secondsLeft) }}<button type="button" @click="nextQuestion">回到正在做的题</button></div>

      <div v-if="allDone" class="math-completion">
        <Trophy :size="30" aria-hidden="true" /><div><strong>今天的 5 道挑战完成啦！</strong><p>答对 {{ payload.correct }} 题，收获 {{ payload.earnedEnergy }} 能量。明天再来，让脑筋继续热身。</p></div>
      </div>

      <article v-if="question" class="math-question-card">
        <div class="math-question-heading">
          <h2 id="math-question-title">第 {{ question.id }} / {{ payload.total || 5 }} 题</h2>
          <span v-if="question.status === 'active'" class="math-timer" :class="{ urgent: secondsLeft <= 60 }" role="timer" aria-label="本题剩余时间"><Clock3 :size="16" aria-hidden="true" />{{ mathCountdownLabel(secondsLeft) }}</span>
          <span v-else class="math-reward-badge">答对 +{{ payload.rewardPerQuestion || 100 }} 能量</span>
        </div>

        <template v-if="question.status === 'pending'">
          <div class="math-ready-art" aria-hidden="true"><span>ABC</span><b>×</b><span>DEF</span></div>
          <h3>准备好挑战三位数乘法了吗？</h3>
          <p class="math-support-copy">点击开始才会揭晓题目并计时。准备好纸和笔，慢慢算、认真检查。</p>
          <button class="primary-action-button math-main-button" type="button" :disabled="!canStart || !!busy" @click="startQuestion">{{ busy === 'start' ? '准备题目中…' : '开始本题 · 10 分钟' }}</button>
        </template>

        <template v-else>
          <p class="math-equation" :aria-label="`${question.left} 乘以 ${question.right}`"><span>{{ question.left }}</span><b>×</b><span>{{ question.right }}</span></p>
          <form v-if="question.status === 'active'" class="math-answer-form" @submit.prevent="submitAnswer">
            <label for="fun-math-answer">你的答案</label>
            <input id="fun-math-answer" ref="answerInput" v-model="answer" type="text" inputmode="numeric" pattern="[0-9]*" maxlength="6" autocomplete="off" placeholder="输入计算结果" :disabled="!!busy || secondsLeft <= 0" aria-describedby="fun-math-answer-help" />
            <p id="fun-math-answer-help">检查好了再提交，每题只有一次正式作答机会。</p>
            <button class="primary-action-button math-main-button" type="submit" :disabled="!canSubmit">{{ busy === 'answer' ? '正在核对…' : secondsLeft <= 0 ? '时间到，正在同步结果…' : '提交答案' }}</button>
          </form>
          <div v-else-if="finished" class="math-result" :class="question.status">
            <strong>{{ mathQuestionLabel(question) }}{{ question.status === 'correct' ? ` · +${question.reward || 100} 能量` : ' · 本题未获得能量' }}</strong>
            <p v-if="question.submittedAnswer != null">你的答案：{{ question.submittedAnswer }}</p>
            <p class="math-correct-answer">正确答案：<b>{{ question.answer }}</b></p>
            <p>{{ question.status === 'correct' ? '细心的计算值得一枚猫爪击掌！奖励已记录，无需再次领取。' : question.status === 'expired' ? '本题时间已结束。看看正确答案，下次记得及时提交。' : '把乘数拆成百位、十位和个位，再把三个部分积加起来，试着复盘一下。' }}</p>
          </div>
          <button v-if="finished && (payload.activeQuestionId || payload.nextQuestionId)" class="primary-action-button math-main-button" type="button" :disabled="!!busy" @click="nextQuestion">{{ payload.activeQuestionId ? '继续正在做的题' : '准备下一题 →' }}</button>
          <button v-if="allDone" class="secondary-button math-main-button" type="button" @click="go('/cat-world')">去看看猫咪 →</button>
        </template>
      </article>
    </section>

    <aside class="math-rules" aria-label="趣味数学规则">
      <strong><Clock3 :size="16" aria-hidden="true" /> 小小约定</strong>
      <ul>
        <li>每天固定随机 5 题，刷新页面不会换题。开始后离开页面，计时也会继续。</li>
        <li>每题限时 10 分钟；限时内答对固定获得 100 猫咪能量，不叠加周末或节庆倍率。</li>
        <li>每题一次提交，答错或超时不发奖。以服务器收到答案的时间和判定为准。</li>
        <li>每天北京时间 00:00 刷新，跨天未完成的题目会结束，请留意剩余时间。</li>
      </ul>
    </aside>
  </section>
</template>

<style scoped>
.fun-math-page { max-width: 1020px; margin-inline: auto; color: #173d33; }
.math-hero { display: flex; align-items: center; justify-content: space-between; gap: 24px; padding: 32px; overflow: hidden; border: 1px solid #c6e5d7; background: linear-gradient(115deg, #ecf8f1, #fff9e9); }
.math-kicker { display: flex; align-items: center; gap: 7px; color: #397c67; font-size: 12px; font-weight: 800; letter-spacing: .13em; margin: 0 0 10px; }
.math-hero h1 { margin: 0; font-size: clamp(28px, 5vw, 40px); line-height: 1.15; }
.math-title-dot { color: #efb74c; }
.math-hero-copy > p:not(.math-kicker) { margin: 12px 0; color: #527264; }
.math-hero-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.math-hero-tags span { padding: 5px 10px; border: 1px solid #c5dfd2; border-radius: 100px; background: #ffffff9c; font-size: 12px; }
.math-hero-symbol { position: relative; display: grid; place-items: center; flex: 0 0 116px; height: 116px; background: #d7eee1; border-radius: 30px; transform: rotate(8deg); color: #24664e; border: 2px solid #fff; box-shadow: 6px 8px 0 #cedfb46e; }
.math-hero-symbol span { position: absolute; top: -12px; right: -6px; display: grid; place-items: center; border-radius: 50%; background: #ffe19a; width: 42px; height: 42px; font-size: 32px; }
.math-hero-symbol small { font-size: 10px; letter-spacing: .09em; font-weight: 900; }
.math-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-block: 20px; }
.math-stats > div { display: grid; gap: 7px; padding: 19px 22px; border: 1px solid #d9e5dd; border-radius: 16px; background: #fff; }
.math-stats span { color: #5f786d; font-size: 13px; display: flex; align-items: center; gap: 5px; }
.math-stats strong { font-size: clamp(18px, 3vw, 26px); font-variant-numeric: tabular-nums; white-space: nowrap; }
.math-stats small { color: #6a7c73; font-size: 12px; }
.math-stats .math-energy { background: #fff8e5; border-color: #ecdbac; }
.math-energy strong { color: #986512; }
.math-workspace { overflow: hidden; padding: 0 28px 28px; background: #fff; border-color: #d1e2d8; }
.math-progress-track { height: 5px; background: #eaf1ec; margin: 0 -28px; }
.math-progress-track span { display: block; height: 100%; background: #47a17b; transition: width .35s; }
.math-workspace-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 22px 0 18px; }
.math-sync-button { display: inline-flex; align-items: center; gap: 6px; border: 0; color: #507365; background: transparent; padding: 8px 0 8px 8px; font-size: 12px; cursor: pointer; }
.math-question-steps { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
.math-question-steps button { display: grid; justify-items: center; gap: 6px; padding: 12px 5px; background: #f6f8f6; color: #718176; border: 1px solid #e0e7e0; border-radius: 14px; cursor: pointer; }
.math-step-number { display: grid; place-items: center; width: 27px; height: 27px; border-radius: 50%; background: #e4ece5; font-weight: 800; }
.math-question-steps small { font-size: 11px; }
.math-question-steps .correct { background: #eef9f2; color: #24754e; }
.math-question-steps .correct .math-step-number { background: #d2efdb; }
.math-question-steps .incorrect, .math-question-steps .expired { color: #8b6952; background: #fcf7ef; }
.math-question-steps .selected { border: 2px solid #357b5d; padding: 11px 4px; box-shadow: 0 0 0 3px #357b5d0c; }
.math-question-steps button:disabled { cursor: default; opacity: .65; }
.math-error, .math-notice, .math-active-notice { margin: 18px 0 0; border-radius: 10px; padding: 12px 14px; font-size: 13px; line-height: 1.65; }
.math-error { background: #fff0ed; color: #a13b27; }
.math-notice { background: #eaf7ef; color: #2e7350; }
.math-active-notice { background: #fff6db; color: #80601d; }
.math-active-notice button { margin-left: 10px; padding: 4px 8px; border: 0; border-radius: 5px; background: #f2e6c0; color: inherit; }
.math-question-card { padding: 26px 0 0; text-align: center; }
.math-question-heading { display: flex; gap: 10px; align-items: center; justify-content: space-between; text-align: left; }
.math-question-heading h2 { margin: 0; font-size: 16px; }
.math-timer, .math-reward-badge { display: inline-flex; align-items: center; gap: 6px; background: #edf6f1; border-radius: 100px; padding: 7px 11px; font-size: 13px; color: #296d51; }
.math-timer { font-size: 19px; font-weight: 800; font-variant-numeric: tabular-nums; }
.math-timer.urgent { background: #fff0e5; color: #b25122; }
.math-ready-art { display: flex; align-items: center; justify-content: center; gap: 14px; padding: 35px 0 10px; color: #4c8169; font-size: 32px; font-weight: 800; letter-spacing: .04em; }
.math-ready-art span { background: #eef7f1; padding: 11px 16px; border-radius: 13px; }
.math-ready-art b { color: #bda166; }
.math-question-card h3 { margin: 18px 0 10px; font-size: 21px; }
.math-support-copy { color: #6c8074; margin: 0 auto 24px; max-width: 410px; line-height: 1.8; font-size: 14px; }
.math-equation { display: flex; justify-content: center; align-items: center; gap: 20px; margin: 34px 0 26px; font-size: clamp(32px, 7vw, 64px); font-weight: 800; font-variant-numeric: tabular-nums; letter-spacing: .03em; }
.math-equation b { font-weight: 400; color: #b6ab87; }
.math-answer-form { max-width: 380px; margin-inline: auto; text-align: left; }
.math-answer-form label { display: block; margin-bottom: 8px; font-size: 13px; font-weight: 700; }
.math-answer-form input { box-sizing: border-box; width: 100%; border: 2px solid #b9d8c5; border-radius: 12px; padding: 15px 16px; color: #173d33; background: #f9fcfa; font-size: 25px; text-align: center; letter-spacing: .06em; }
.math-answer-form input:focus { outline: 3px solid #dceee3; border-color: #3d8a64; }
.math-answer-form input::placeholder { font-size: 17px; letter-spacing: 0; color: #8fa899; }
.math-answer-form p { color: #768679; font-size: 12px; line-height: 1.6; margin: 10px 0 20px; }
.math-main-button { width: min(100%, 380px); min-height: 48px; margin-inline: auto; padding: 13px 20px; font-weight: 800; border-radius: 11px; }
.math-result { margin: 0 auto 24px; max-width: 480px; border-radius: 16px; padding: 20px; background: #f4f7f1; }
.math-result.correct { background: #eaf7ef; color: #24714a; }
.math-result.incorrect, .math-result.expired { background: #fff6e8; color: #8d5f30; }
.math-result strong { font-size: 18px; }
.math-result p { font-size: 13px; line-height: 1.8; margin: 12px 0 0; }
.math-result .math-correct-answer { font-size: 18px; }
.math-completion { display: flex; align-items: center; gap: 15px; margin-top: 22px; background: #fff7df; border: 1px solid #ecdda9; border-radius: 14px; padding: 18px; color: #8b651e; }
.math-completion > svg { flex-shrink: 0; }
.math-completion p { font-size: 13px; line-height: 1.7; margin: 6px 0 0; }
.math-rules { margin-top: 22px; padding: 5px 7px; color: #697c6f; font-size: 12px; line-height: 1.9; }
.math-rules strong { display: flex; gap: 6px; align-items: center; font-size: 13px; color: #4c6a59; }
.math-rules ul { padding-left: 20px; margin: 10px 0; }
@media (max-width: 600px) {
  .math-hero { padding: 22px 19px; gap: 12px; }
  .math-hero-symbol { flex-basis: 66px; height: 76px; border-radius: 21px; }
  .math-hero-symbol > svg { width: 30px; height: 30px; }
  .math-hero-symbol span { font-size: 24px; width: 30px; height: 30px; top: -9px; right: -7px; }
  .math-hero-symbol small { font-size: 7px; }
  .math-hero-copy > p:not(.math-kicker) { font-size: 13px; }
  .math-hero-tags { gap: 5px; }
  .math-hero-tags span { font-size: 10px; padding: 4px 7px; }
  .math-kicker { font-size: 9px; }
  .math-stats { gap: 7px; margin-block: 13px; }
  .math-stats > div { gap: 6px; padding: 13px 9px; border-radius: 12px; }
  .math-stats span, .math-stats small { font-size: 10px; }
  .math-stats strong { font-size: 18px; }
  .math-stats > div:first-child strong { font-size: 12px; }
  .math-workspace { padding: 0 16px 22px; }
  .math-progress-track { margin-inline: -16px; }
  .math-question-steps { gap: 6px; }
  .math-question-steps button { border-radius: 11px; }
  .math-ready-art { font-size: 25px; }
  .math-ready-art span { padding: 10px 12px; }
  .math-question-card h3 { font-size: 18px; }
  .math-equation { gap: 13px; }
  .math-reward-badge { font-size: 11px; padding: 6px 8px; }
}
</style>
