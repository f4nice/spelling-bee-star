<script setup>
import { nextTick, ref, watch } from "vue";

import ChallengeAnswerPanel from "./ChallengeAnswerPanel.vue";
import SpeechAudioPlayer from "./SpeechAudioPlayer.vue";
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

const emit = defineEmits(["update:spelling", "submit"]);
const { playAudio } = useAudioPlayback();
const usSpeechPlayer = ref(null);
const gbSpeechPlayer = ref(null);

function playCurrentAudio() {
  if (props.state.challenge_audio_sources?.us) {
    playAudio("challenge-audio-us", props.state.current_word?.word || "", "en-US");
    return;
  }
  usSpeechPlayer.value?.play();
}

function playBritishAudio() {
  if (props.state.challenge_audio_sources?.gb) {
    playAudio("challenge-audio-gb", props.state.current_word?.word || "", "en-GB");
    return;
  }
  gbSpeechPlayer.value?.play();
}

watch(
  () => props.state.current_word?.id,
  async (wordId) => {
    if (!wordId) return;
    await nextTick();
    playCurrentAudio();
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
        <label>
          <span>美音</span>
          <audio
            v-if="state.challenge_audio_sources?.us"
            id="challenge-audio-us"
            preload="auto"
            controls
            :src="state.challenge_audio_sources?.us"
          />
          <SpeechAudioPlayer
            v-else
            ref="usSpeechPlayer"
            :text="state.current_word.word"
            lang="en-US"
            label="美音"
          />
        </label>
        <label>
          <span>英音</span>
          <audio
            v-if="state.challenge_audio_sources?.gb"
            id="challenge-audio-gb"
            preload="auto"
            controls
            :src="state.challenge_audio_sources?.gb"
          />
          <SpeechAudioPlayer
            v-else
            ref="gbSpeechPlayer"
            :text="state.current_word.word"
            lang="en-GB"
            label="英音"
          />
        </label>
      </div>

      <ChallengeAnswerPanel
        :spelling="spelling"
        :submitting="submitting"
        @update:spelling="emit('update:spelling', $event)"
        @submit="emit('submit')"
      />
    </div>
  </article>
</template>
