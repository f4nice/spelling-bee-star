<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";

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
  markingAudioIssue: {
    type: Boolean,
    default: false,
  },
  markingImageIssue: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:spelling", "submit", "mark-audio-issue", "mark-image-issue"]);
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

function toggleAudioIssue() {
  emit("mark-audio-issue", !props.state.current_word?.audio_issue);
}

function toggleImageIssue() {
  emit("mark-image-issue", !props.state.current_word?.image_issue);
}

function shouldHandleAudioShortcut(event) {
  if (!["ArrowUp", "ArrowDown"].includes(event.key)) return false;
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return false;
  if (document.querySelector(".challenge-answer-modal")) return false;

  const target = event.target;
  if (target?.isContentEditable) return false;
  const tagName = target?.tagName?.toLowerCase();
  if (["textarea", "select", "button", "audio"].includes(tagName)) return false;
  if (tagName === "input" && !target.classList?.contains("challenge-spelling-input")) return false;
  return true;
}

function handleAudioShortcut(event) {
  if (!shouldHandleAudioShortcut(event)) return;
  event.preventDefault();
  if (event.key === "ArrowUp") {
    playCurrentAudio();
    return;
  }
  playBritishAudio();
}

onMounted(() => {
  window.addEventListener("keydown", handleAudioShortcut);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleAudioShortcut);
});

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

      <div class="challenge-audio-row">
        <label>
          <span class="challenge-audio-label-head">
            <span>美音</span>
          </span>
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
        <div class="challenge-media-issue-actions">
          <button
            class="challenge-media-issue-button challenge-image-issue-button"
            :class="{ active: state.current_word?.image_issue }"
            type="button"
            :disabled="markingImageIssue"
            @click.prevent="toggleImageIssue"
          >
            {{ state.current_word?.image_issue ? "图片待修" : "图片不对" }}
          </button>
          <button
            class="challenge-media-issue-button challenge-audio-issue-button"
            :class="{ active: state.current_word?.audio_issue }"
            type="button"
            :disabled="markingAudioIssue"
            @click.prevent="toggleAudioIssue"
          >
            {{ state.current_word?.audio_issue ? "音频待修" : "音频不准" }}
          </button>
        </div>
      </div>
    </div>

    <div class="challenge-word-body">
      <ChallengeWordPrompt :word="state.current_word" :masked-example="state.masked_example" />

      <ChallengeAnswerPanel
        :spelling="spelling"
        :submitting="submitting"
        @update:spelling="emit('update:spelling', $event)"
        @submit="emit('submit')"
      />
    </div>
  </article>
</template>
