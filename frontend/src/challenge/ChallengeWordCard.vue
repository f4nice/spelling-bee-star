<script setup>
import { useAudioPlayback } from "../shared/useAudioPlayback.js";

const props = defineProps({
  state: {
    type: Object,
    required: true,
  },
  spelling: {
    type: String,
    required: true,
  },
  submitting: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:spelling", "submit", "strip-digits"]);
const { playAudio } = useAudioPlayback();

function submitAnswer() {
  if (!props.spelling.trim() || props.submitting) return;
  emit("submit");
}
</script>

<template>
  <article class="challenge-word-card">
    <div class="challenge-word-prompt">
      <p class="section-kicker">当前单词</p>
      <h2>{{ state.current_word.chinese_definition || state.current_word.english_definition || "听音拼写" }}</h2>
      <p v-if="state.current_word.english_example">{{ state.current_word.english_example }}</p>
    </div>

    <div class="challenge-audio-row">
      <button type="button" class="secondary-button" @click="playAudio('challenge-audio-us')">美音</button>
      <audio id="challenge-audio-us" preload="none" :src="state.challenge_audio_sources?.us" />
      <button type="button" class="secondary-button" @click="playAudio('challenge-audio-gb')">英音</button>
      <audio id="challenge-audio-gb" preload="none" :src="state.challenge_audio_sources?.gb" />
    </div>

    <div class="challenge-answer-panel" role="group" aria-label="拼写答案">
      <input
        :value="spelling"
        class="challenge-spelling-input"
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        placeholder="输入英文拼写"
        @input="emit('update:spelling', $event.target.value)"
        @keydown.enter.prevent="submitAnswer"
      >
      <div class="challenge-actions">
        <button type="button" class="secondary-button" @click="emit('strip-digits')">去掉数字</button>
        <button type="button" :disabled="submitting || !spelling.trim()" @click="submitAnswer">
          {{ submitting ? "提交中..." : "提交答案" }}
        </button>
      </div>
    </div>
  </article>
</template>
