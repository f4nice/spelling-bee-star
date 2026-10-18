<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { fetchJson } from "../utils.js";
import { wordAudioCandidates } from "../wordAudioSource.js";

const STORAGE_KEY = "speakeasy.wordAutoStudy";
const AUTO_STUDY_READ_COUNT = 2;
const AUTO_STUDY_REPLAY_GAP_MS = 350;
const AUTO_STUDY_FALLBACK_READ_MS = 1800;

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  wordNavUrl: {
    type: Function,
    required: true,
  },
  navigateWord: {
    type: Function,
    default: null,
  },
  playAudio: {
    type: Function,
    required: true,
  },
});

const intervalSeconds = ref(6);
const isAutoStudying = ref(false);
const remainingSeconds = ref(0);
const currentReadCount = ref(0);
const isCountingDown = ref(false);
const requiresMobileAudioUnlock = ref(false);
let timerId = null;
let countdownId = null;
let audioReplayIds = [];
let awaitingWordId = null;
let isPausedByUser = false;
let studyRunId = 0;
let cancelAudioWait = null;

const previousWordUrl = computed(() => props.wordNavUrl(props.data.navigation.previous_word_id));
const nextWordUrl = computed(() => props.wordNavUrl(props.data.navigation.next_word_id));
const statusText = computed(() => {
  if (requiresMobileAudioUnlock.value) return "点击自动学习开启声音";
  if (!isAutoStudying.value) return "未开始";
  if (!isCountingDown.value) return `朗读 ${Math.max(currentReadCount.value, 1)} / ${AUTO_STUDY_READ_COUNT}`;
  return `已读 ${AUTO_STUDY_READ_COUNT} 次，${remainingSeconds.value || intervalSeconds.value} 秒后下一个`;
});

function readStoredState() {
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function writeStoredState(active) {
  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      active,
      intervalSeconds: Math.max(Number(intervalSeconds.value) || 1, 1),
    }),
  );
}

function clearTimers() {
  clearCountdownTimers();
  clearAudioReplayTimers();
}

function clearCountdownTimers() {
  if (timerId) {
    window.clearTimeout(timerId);
    timerId = null;
  }
  if (countdownId) {
    window.clearInterval(countdownId);
    countdownId = null;
  }
  isCountingDown.value = false;
}

function clearAudioReplayTimers() {
  audioReplayIds.forEach((id) => window.clearTimeout(id));
  audioReplayIds = [];
}

function goNext() {
  const nextWordId = props.data.navigation.next_word_id;
  if (typeof props.navigateWord === "function") {
    // Keep the SPA document alive between words. A full page reload loses the
    // user activation that allowed the first audio playback, so browsers
    // commonly block every later word's audio as autoplay.
    if (Number(nextWordId) === Number(props.data.word?.id)) {
      playCurrentWordTwiceThenSchedule();
      return;
    }
    awaitingWordId = Number(nextWordId);
    props.navigateWord(nextWordUrl.value);
    return;
  }
  window.location.href = nextWordUrl.value;
}

async function prefetchNextWord() {
  try {
    const nextUrl = new URL(nextWordUrl.value, window.location.origin);
    const apiUrl = `/api/vue${nextUrl.pathname}${nextUrl.search}`;
    const payload = await fetchJson(apiUrl);
    if (payload?.word?.image_url) {
      const image = new Image();
      image.src = payload.word.image_url;
    }
    Object.values(payload?.audio_sources || {}).filter(Boolean).forEach((url) => {
      const link = document.createElement("link");
      link.rel = "prefetch";
      link.as = "audio";
      link.href = url;
      document.head.appendChild(link);
    });
  } catch {
    // Prefetch is opportunistic; normal navigation still works if it fails.
  }
}

function scheduleNext() {
  clearCountdownTimers();
  const seconds = Math.max(Number(intervalSeconds.value) || 1, 1);
  remainingSeconds.value = seconds;
  isCountingDown.value = true;
  countdownId = window.setInterval(() => {
    remainingSeconds.value = Math.max(remainingSeconds.value - 1, 0);
  }, 1000);
  timerId = window.setTimeout(goNext, seconds * 1000);
}

function currentAudioTarget() {
  const word = props.data.word?.word || "";
  const [candidate] = wordAudioCandidates(props.data);
  return {
    audioId: "auto-study-audio",
    source: candidate?.source || "",
    text: word,
    lang: candidate?.lang || "en-US",
  };
}

function isMobileBrowser() {
  return window.matchMedia?.("(max-width: 900px)").matches;
}

function unlockAudioFromUserGesture() {
  const target = currentAudioTarget();
  const audio = document.getElementById(target.audioId);
  if (!audio || !target.source) return;
  if (audio.getAttribute("src") !== target.source) audio.setAttribute("src", target.source);
  audio.play().catch(() => {});
}

async function playCurrentWord(runId = studyRunId) {
  const word = props.data.word?.word || "";
  const candidates = wordAudioCandidates(props.data);
  isPausedByUser = false;
  const audio = document.getElementById("auto-study-audio");
  for (const candidate of candidates) {
    const target = {
      audioId: "auto-study-audio",
      source: candidate.source,
      text: word,
      lang: candidate.lang,
    };
    if (audio && target.source && audio.getAttribute("src") !== target.source) {
      audio.setAttribute("src", target.source);
    }
    const played = await props.playAudio(target.audioId, target.text, target.lang, { fallbackToSpeech: false });
    if (played) {
      if (runId !== studyRunId || !isAutoStudying.value) return null;
      return target;
    }
  }
  const target = currentAudioTarget();
  await props.playAudio(target.audioId, target.text, target.lang, { fallbackToSpeech: true });
  if (runId !== studyRunId || !isAutoStudying.value) return null;
  return target;
}

function cancelPendingAudioWait() {
  const cancel = cancelAudioWait;
  cancelAudioWait = null;
  if (cancel) cancel();
}

function waitForAudioToFinish(audioId, runId = studyRunId) {
  if (runId !== studyRunId || !isAutoStudying.value) return Promise.resolve(false);
  const audio = document.getElementById(audioId);
  if (!audio) {
    return new Promise((resolve) => {
      let fallbackId = window.setTimeout(() => {
        if (cancelAudioWait === cancel) cancelAudioWait = null;
        resolve(true);
      }, AUTO_STUDY_FALLBACK_READ_MS);
      const cancel = () => {
        window.clearTimeout(fallbackId);
        fallbackId = null;
        if (cancelAudioWait === cancel) cancelAudioWait = null;
        resolve(false);
      };
      cancelAudioWait = cancel;
    });
  }
  const durationMs = Number.isFinite(audio.duration) && audio.duration > 0
    ? Math.min(Math.max((audio.duration + 0.35) * 1000, AUTO_STUDY_FALLBACK_READ_MS), 6000)
    : AUTO_STUDY_FALLBACK_READ_MS;
  return new Promise((resolve) => {
    let finished = false;
    let fallbackId = null;
    let startedAt = performance.now();
    let remainingMs = durationMs;
    const clearFallback = () => {
      if (fallbackId) window.clearTimeout(fallbackId);
      fallbackId = null;
    };
    const scheduleFallback = () => {
      clearFallback();
      if (isPausedByUser || runId !== studyRunId || !isAutoStudying.value) return;
      startedAt = performance.now();
      fallbackId = window.setTimeout(finish, remainingMs);
    };
    const finish = (completed = true) => {
      if (finished) return;
      finished = true;
      clearFallback();
      audio.removeEventListener("ended", finish);
      audio.removeEventListener("error", finish);
      audio.removeEventListener("pause", handlePause);
      audio.removeEventListener("play", handlePlay);
      if (cancelAudioWait === cancel) cancelAudioWait = null;
      resolve(completed);
    };
    const cancel = () => finish(false);
    const handlePause = () => {
      if (!isPausedByUser) return;
      remainingMs = Math.max(remainingMs - (performance.now() - startedAt), 0);
      clearFallback();
    };
    const handlePlay = () => {
      if (!isPausedByUser) scheduleFallback();
    };
    audio.addEventListener("ended", finish, { once: true });
    audio.addEventListener("error", finish, { once: true });
    audio.addEventListener("pause", handlePause);
    audio.addEventListener("play", handlePlay);
    cancelAudioWait = cancel;
    scheduleFallback();
  });
}

function toggleAudioFromImage() {
  if (!isAutoStudying.value) return;
  const audio = document.getElementById("auto-study-audio");
  if (!audio) return;
  if (audio.paused) {
    isPausedByUser = false;
    audio.play().catch(() => {
      isPausedByUser = true;
    });
    return;
  }
  isPausedByUser = true;
  audio.pause();
}

async function playAutoStudyRead(readCount = 1, runId = studyRunId) {
  if (!isAutoStudying.value || runId !== studyRunId) return;
  currentReadCount.value = readCount;
  const target = await playCurrentWord(runId);
  if (!target) return;
  const completed = await waitForAudioToFinish(target.audioId, runId);
  if (!completed || !isAutoStudying.value || runId !== studyRunId) return;
  if (readCount >= AUTO_STUDY_READ_COUNT) {
    scheduleNext();
    return;
  }
  audioReplayIds.push(window.setTimeout(() => playAutoStudyRead(readCount + 1, runId), AUTO_STUDY_REPLAY_GAP_MS));
}

function playCurrentWordTwiceThenSchedule() {
  clearCountdownTimers();
  clearAudioReplayTimers();
  cancelPendingAudioWait();
  isPausedByUser = false;
  remainingSeconds.value = 0;
  currentReadCount.value = 0;
  playAutoStudyRead(1, studyRunId);
}

function startAutoStudy() {
  studyRunId += 1;
  cancelPendingAudioWait();
  requiresMobileAudioUnlock.value = false;
  isAutoStudying.value = true;
  writeStoredState(true);
  playCurrentWordTwiceThenSchedule();
}

function stopAutoStudy() {
  studyRunId += 1;
  cancelPendingAudioWait();
  isAutoStudying.value = false;
  awaitingWordId = null;
  remainingSeconds.value = 0;
  currentReadCount.value = 0;
  isCountingDown.value = false;
  writeStoredState(false);
  clearTimers();
  const audio = document.getElementById("auto-study-audio");
  if (audio) {
    audio.pause();
    audio.currentTime = 0;
  }
}

watch(() => props.data.word?.id, (wordId) => {
  if (!isAutoStudying.value || !awaitingWordId || Number(wordId) !== awaitingWordId) return;
  awaitingWordId = null;
  playCurrentWordTwiceThenSchedule();
});

onMounted(() => {
  window.addEventListener("speakeasy:audio-toggle", toggleAudioFromImage);
  const stored = readStoredState();
  if (stored.intervalSeconds) intervalSeconds.value = stored.intervalSeconds;
  prefetchNextWord();
  if (stored.active) {
    if (isMobileBrowser()) {
      requiresMobileAudioUnlock.value = true;
      writeStoredState(false);
    } else {
      isAutoStudying.value = true;
      playCurrentWordTwiceThenSchedule();
    }
  }
});

onBeforeUnmount(() => {
  studyRunId += 1;
  isAutoStudying.value = false;
  window.removeEventListener("speakeasy:audio-toggle", toggleAudioFromImage);
  cancelPendingAudioWait();
  clearTimers();
  const audio = document.getElementById("auto-study-audio");
  if (audio) audio.pause();
});
</script>

<template>
  <div class="detail-study-row">
    <div class="auto-study-controls word-study-controls">
      <a class="secondary-button" :href="previousWordUrl">上一个</a>
      <a class="secondary-button" :href="nextWordUrl">下一个</a>
      <label>
        <span>间隔</span>
        <input v-model.number="intervalSeconds" type="number" min="1" max="60">
        <span>秒</span>
      </label>
      <button class="secondary-button" type="button" :disabled="isAutoStudying" @pointerdown="unlockAudioFromUserGesture" @click="startAutoStudy">
        自动学习
      </button>
      <button class="secondary-button" type="button" :disabled="!isAutoStudying" @click="stopAutoStudy">
        停止
      </button>
      <span class="auto-study-status">{{ statusText }}</span>
    </div>
    <audio id="auto-study-audio" hidden playsinline preload="auto"></audio>
  </div>
</template>
