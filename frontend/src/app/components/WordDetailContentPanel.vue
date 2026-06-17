<script setup>
import WordAudioPanel from "./WordAudioPanel.vue";
import WordDetailDefinitionPanel from "./WordDetailDefinitionPanel.vue";
import WordDetailHeading from "./WordDetailHeading.vue";
import WordStudyNav from "./WordStudyNav.vue";

defineProps({
  data: {
    type: Object,
    required: true,
  },
  wordEdit: {
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
  wordNavUrl: {
    type: Function,
    required: true,
  },
  saveWordField: {
    type: Function,
    required: true,
  },
  refreshWord: {
    type: Function,
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
  <article class="panel detail-panel">
    <WordStudyNav :data="data" :word-nav-url="wordNavUrl" />
    <WordDetailHeading
      :data="data"
      :word-edit="wordEdit"
      :save-word-field="saveWordField"
      :refresh-word="refreshWord"
    />

    <WordAudioPanel
      :data="data"
      :audio-options="audioOptions"
      :recorder-state="recorderState"
      :play-audio="playAudio"
      :fetch-audio-options="fetchAudioOptions"
      :start-recording="startRecording"
      :choose-audio="chooseAudio"
      :stop-recording="stopRecording"
      :save-recording="saveRecording"
    />

    <WordDetailDefinitionPanel :data="data" :word-edit="wordEdit" :save-word-field="saveWordField" />
  </article>
</template>
