<script setup>
import WordAudioAccentPanel from "./WordAudioAccentPanel.vue";

defineProps({
  data: {
    type: Object,
    required: true,
  },
  audioOptions: {
    type: Object,
    required: true,
  },
  accents: {
    type: Array,
    required: true,
  },
  playAudio: {
    type: Function,
    required: true,
  },
  fetchAudioOptions: {
    type: Function,
    required: true,
  },
  startRecording: {
    type: Function,
    required: true,
  },
  chooseAudio: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="audio-row">
    <WordAudioAccentPanel
      v-for="accent in accents"
      :key="accent.key"
      :accent="accent"
      :data="data"
      :options="audioOptions[accent.key] || []"
      :play-audio="playAudio"
      :fetch-audio-options="fetchAudioOptions"
      :start-recording="startRecording"
      :choose-audio="chooseAudio"
    />
  </div>
</template>
