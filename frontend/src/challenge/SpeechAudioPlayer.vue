<script setup>
import { computed, onBeforeUnmount, ref } from "vue";

const props = defineProps({
  text: {
    type: String,
    default: "",
  },
  lang: {
    type: String,
    default: "en-US",
  },
  label: {
    type: String,
    default: "播放",
  },
});

const isPlaying = ref(false);
const elapsed = ref(0);
const duration = ref(2);
let utterance = null;
let startedAt = 0;
let frameId = 0;

const percent = computed(() => {
  if (!duration.value) return 0;
  return Math.min((elapsed.value / duration.value) * 100, 100);
});

const timeLabel = computed(() => `${formatTime(elapsed.value)} / ${formatTime(duration.value)}`);

function formatTime(seconds) {
  const safeSeconds = Math.max(Math.round(seconds), 0);
  return `0:${String(safeSeconds).padStart(2, "0")}`;
}

function estimateDuration(text) {
  const letters = String(text || "").replace(/\s+/g, "");
  return Math.max(1, Math.min(Math.ceil(letters.length * 0.12), 8));
}

function updateProgress() {
  if (!isPlaying.value) return;
  elapsed.value = Math.min((Date.now() - startedAt) / 1000, duration.value);
  if (elapsed.value < duration.value) {
    frameId = window.requestAnimationFrame(updateProgress);
  }
}

function resetProgress() {
  if (frameId) {
    window.cancelAnimationFrame(frameId);
    frameId = 0;
  }
  isPlaying.value = false;
  elapsed.value = 0;
}

function stop() {
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  utterance = null;
  resetProgress();
}

function play() {
  if (!props.text || !window.speechSynthesis) return;
  stop();
  duration.value = estimateDuration(props.text);
  utterance = new SpeechSynthesisUtterance(props.text);
  utterance.lang = props.lang;
  utterance.onend = resetProgress;
  utterance.onerror = resetProgress;
  isPlaying.value = true;
  startedAt = Date.now();
  updateProgress();
  window.speechSynthesis.speak(utterance);
}

function toggle() {
  if (isPlaying.value) {
    stop();
    return;
  }
  play();
}

defineExpose({
  play,
  stop,
});

onBeforeUnmount(stop);
</script>

<template>
  <div class="speech-audio-player" :class="{ 'is-playing': isPlaying }">
    <button
      type="button"
      class="speech-audio-play"
      :aria-label="isPlaying ? `停止${label}` : `播放${label}`"
      @click="toggle"
    >
      <span aria-hidden="true">{{ isPlaying ? "■" : "▶" }}</span>
    </button>
    <div class="speech-audio-track" aria-hidden="true">
      <span :style="{ width: `${percent}%` }"></span>
    </div>
    <span class="speech-audio-time">{{ timeLabel }}</span>
  </div>
</template>
