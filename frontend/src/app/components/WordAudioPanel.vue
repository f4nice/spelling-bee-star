<script setup>
import { wordAudioAccents } from "../wordAudioAccents.js";
import WordAudioAccentList from "./WordAudioAccentList.vue";
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
</script>

<template>
  <WordAudioAccentList
    :data="data"
    :audio-options="audioOptions"
    :accents="wordAudioAccents"
    :play-audio="playAudio"
    :fetch-audio-options="fetchAudioOptions"
    :start-recording="startRecording"
    :choose-audio="chooseAudio"
  />

  <WordRecorderPanel
    :recorder-state="recorderState"
    :stop-recording="stopRecording"
    :save-recording="saveRecording"
  />
</template>
