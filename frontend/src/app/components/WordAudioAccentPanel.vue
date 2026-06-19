<script setup>
import { ref } from "vue";

import { wordAudioAccentPanelProps } from "../props/wordAudioAccentPanelProps.js";
import WordAudioActions from "./WordAudioActions.vue";
import WordAudioManagerModal from "./WordAudioManagerModal.vue";

defineProps(wordAudioAccentPanelProps);

const showManager = ref(false);
</script>

<template>
  <div class="audio-accent-panel">
    <span>{{ accent.label }}</span>
    <WordAudioActions
      :accent="accent"
      :audio-src="data.audio_sources[accent.key]"
      :can-edit="data.can_edit"
      :play-audio="playAudio"
      :fetch-audio-options="fetchAudioOptions"
      @manage-audio="showManager = true"
    />
    <WordAudioManagerModal
      v-if="showManager"
      :accent="accent"
      :options="options"
      :fetch-audio-options="fetchAudioOptions"
      :choose-audio="chooseAudio"
      :upload-audio="uploadAudio"
      @close="showManager = false"
    />
  </div>
</template>
