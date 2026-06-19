<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { fetchJson } from "../utils.js";

const STORAGE_KEY = "speakeasy.wordAutoStudy";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  wordNavUrl: {
    type: Function,
    required: true,
  },
});

const intervalSeconds = ref(6);
const isAutoStudying = ref(false);
const remainingSeconds = ref(0);
let timerId = null;
let countdownId = null;

const previousWordUrl = computed(() => props.wordNavUrl(props.data.navigation.previous_word_id));
const nextWordUrl = computed(() => props.wordNavUrl(props.data.navigation.next_word_id));
const statusText = computed(() => {
  if (!isAutoStudying.value) return "未开始";
  return `${remainingSeconds.value || intervalSeconds.value} 秒后下一个`;
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
  if (timerId) {
    window.clearTimeout(timerId);
    timerId = null;
  }
  if (countdownId) {
    window.clearInterval(countdownId);
    countdownId = null;
  }
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
  clearTimers();
  const seconds = Math.max(Number(intervalSeconds.value) || 1, 1);
  remainingSeconds.value = seconds;
  countdownId = window.setInterval(() => {
    remainingSeconds.value = Math.max(remainingSeconds.value - 1, 0);
  }, 1000);
  timerId = window.setTimeout(goNext, seconds * 1000);
}

function startAutoStudy() {
  isAutoStudying.value = true;
  writeStoredState(true);
  scheduleNext();
}

function stopAutoStudy() {
  isAutoStudying.value = false;
  remainingSeconds.value = 0;
  writeStoredState(false);
  clearTimers();
}

onMounted(() => {
  const stored = readStoredState();
  if (stored.intervalSeconds) intervalSeconds.value = stored.intervalSeconds;
  prefetchNextWord();
  if (stored.active) {
    isAutoStudying.value = true;
    scheduleNext();
  }
});

onBeforeUnmount(clearTimers);
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
