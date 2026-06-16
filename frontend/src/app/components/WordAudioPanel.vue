<script setup>
import WordAudioAccentPanel from "./WordAudioAccentPanel.vue";
import WordRecorderPanel from "./WordRecorderPanel.vue";

defineProps({
  data: {
    type: Object,
    required: true,
  },
  audioOptions: {
    type: Object,
    required: true,
  },
  recorderState: {
    type: Object,
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
  stopRecording: {
    type: Function,
    required: true,
  },
  saveRecording: {
    type: Function,
    required: true,
  },
});

const accents = [
  { key: "us", label: "美式发音", actionLabel: "朗读美式" },
  { key: "gb", label: "英式发音", actionLabel: "朗读英式" },
];
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

  <WordRecorderPanel
    :recorder-state="recorderState"
    :stop-recording="stopRecording"
    :save-recording="saveRecording"
  />
</template>
