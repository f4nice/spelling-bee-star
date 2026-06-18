<script setup>
import { nextTick, watch } from "vue";

import ChallengeAnswerPanel from "./ChallengeAnswerPanel.vue";
import ChallengeWordPrompt from "./ChallengeWordPrompt.vue";
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

watch(
  () => props.state.current_word?.id,
  async (wordId) => {
    if (!wordId) return;
    await nextTick();
    playAudio("challenge-audio-us");
  },
  { immediate: true },
);
</script>

<template>
  <article class="challenge-card challenge-word-card">
    <div class="challenge-word-media">
      <img v-if="state.challenge_image_url" :src="state.challenge_image_url" :alt="state.current_word.word">
      <div v-else class="image-fallback large">{{ state.current_word.word.slice(0, 1).toUpperCase() }}</div>
    </div>

    <div class="challenge-word-body">
      <ChallengeWordPrompt :word="state.current_word" :masked-example="state.masked_example" />

      <div class="challenge-audio-row">
        <button type="button" class="secondary-button" @click="playAudio('challenge-audio-us')">美音</button>
        <audio id="challenge-audio-us" preload="auto" :src="state.challenge_audio_sources?.us" />
        <button type="button" class="secondary-button" @click="playAudio('challenge-audio-gb')">英音</button>
        <audio id="challenge-audio-gb" preload="auto" :src="state.challenge_audio_sources?.gb" />
      </div>

      <ChallengeAnswerPanel
        :spelling="spelling"
        :submitting="submitting"
        @update:spelling="emit('update:spelling', $event)"
        @submit="emit('submit')"
        @strip-digits="emit('strip-digits')"
      />
    </div>
  </article>
</template>
