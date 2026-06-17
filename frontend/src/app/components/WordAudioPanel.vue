<script setup>
import { wordAudioPanelProps } from "../props/wordAudioPanelProps.js";
import { wordAudioAccents } from "../wordAudioAccents.js";
import WordAudioAccentList from "./WordAudioAccentList.vue";
import WordRecorderPanel from "./WordRecorderPanel.vue";

defineProps(wordAudioPanelProps);
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
