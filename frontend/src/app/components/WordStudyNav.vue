<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { fetchJson } from "../utils.js";

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
let timerId = null;
let countdownId = null;
let audioReplayIds = [];

const previousWordUrl = computed(() => props.wordNavUrl(props.data.navigation.previous_word_id));
const nextWordUrl = computed(() => props.wordNavUrl(props.data.navigation.next_word_id));
const statusText = computed(() => {
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
  const audioSources = props.data.audio_sources || {};
  const word = props.data.word?.word || "";
  if (audioSources.us) {
    return { audioId: "audio-us", text: word, lang: "en-US" };
  }
  if (audioSources.gb) {
    return { audioId: "audio-gb", text: word, lang: "en-GB" };
  }
  return { audioId: "audio-us", text: word, lang: "en-US" };
}

function playCurrentWord() {
  const target = currentAudioTarget();
  props.playAudio(target.audioId, target.text, target.lang);
  return target;
}

function waitForAudioToFinish(audioId) {
  const audio = document.getElementById(audioId);
  if (!audio) {
    return new Promise((resolve) => {
      window.setTimeout(resolve, AUTO_STUDY_FALLBACK_READ_MS);
    });
  }
  const durationMs = Number.isFinite(audio.duration) && audio.duration > 0
    ? Math.min(Math.max((audio.duration + 0.35) * 1000, AUTO_STUDY_FALLBACK_READ_MS), 6000)
    : AUTO_STUDY_FALLBACK_READ_MS;
  return new Promise((resolve) => {
    let finished = false;
    let fallbackId = null;
    const finish = () => {
      if (finished) return;
      finished = true;
      if (fallbackId) window.clearTimeout(fallbackId);
      audio.removeEventListener("ended", finish);
      audio.removeEventListener("error", finish);
      resolve();
    };
    audio.addEventListener("ended", finish, { once: true });
    audio.addEventListener("error", finish, { once: true });
    fallbackId = window.setTimeout(finish, durationMs);
  });
}

async function playAutoStudyRead(readCount = 1) {
  if (!isAutoStudying.value) return;
  currentReadCount.value = readCount;
  const target = playCurrentWord();
  await waitForAudioToFinish(target.audioId);
  if (!isAutoStudying.value) return;
  if (readCount >= AUTO_STUDY_READ_COUNT) {
    scheduleNext();
    return;
  }
  audioReplayIds.push(window.setTimeout(() => playAutoStudyRead(readCount + 1), AUTO_STUDY_REPLAY_GAP_MS));
}

function playCurrentWordTwiceThenSchedule() {
  clearCountdownTimers();
  clearAudioReplayTimers();
  remainingSeconds.value = 0;
  currentReadCount.value = 0;
  playAutoStudyRead(1);
}

function startAutoStudy() {
  isAutoStudying.value = true;
  writeStoredState(true);
  playCurrentWordTwiceThenSchedule();
}

function stopAutoStudy() {
  isAutoStudying.value = false;
  remainingSeconds.value = 0;
  currentReadCount.value = 0;
  isCountingDown.value = false;
  writeStoredState(false);
  clearTimers();
}

onMounted(() => {
  const stored = readStoredState();
  if (stored.intervalSeconds) intervalSeconds.value = stored.intervalSeconds;
  prefetchNextWord();
  if (stored.active) {
    isAutoStudying.value = true;
    playCurrentWordTwiceThenSchedule();
  }
});

onBeforeUnmount(() => {
  isAutoStudying.value = false;
  clearTimers();
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
      <button class="secondary-button" type="button" :disabled="isAutoStudying" @click="startAutoStudy">
        自动学习
      </button>
      <button class="secondary-button" type="button" :disabled="!isAutoStudying" @click="stopAutoStudy">
        停止
      </button>
      <span class="auto-study-status">{{ statusText }}</span>
    </div>
  </div>
</template>
