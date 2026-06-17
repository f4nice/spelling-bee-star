<script setup>
import ChallengeAnswerPanel from "./ChallengeAnswerPanel.vue";
import ChallengeWordPrompt from "./ChallengeWordPrompt.vue";
import { useAudioPlayback } from "../shared/useAudioPlayback.js";

defineProps({
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
</script>

<template>
  <article class="challenge-word-card">
    <ChallengeWordPrompt :word="state.current_word" />

    <div class="challenge-audio-row">
      <button type="button" class="secondary-button" @click="playAudio('challenge-audio-us')">美音</button>
      <audio id="challenge-audio-us" preload="none" :src="state.challenge_audio_sources?.us" />
      <button type="button" class="secondary-button" @click="playAudio('challenge-audio-gb')">英音</button>
      <audio id="challenge-audio-gb" preload="none" :src="state.challenge_audio_sources?.gb" />
    </div>

    <ChallengeAnswerPanel
      :spelling="spelling"
      :submitting="submitting"
      @update:spelling="emit('update:spelling', $event)"
      @submit="emit('submit')"
      @strip-digits="emit('strip-digits')"
    />
  </article>
</template>
