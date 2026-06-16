<script setup>
import WordDetailContentPanel from "../components/WordDetailContentPanel.vue";
import WordMediaPanel from "../components/WordMediaPanel.vue";

defineProps([
  "data",
  "wordEdit",
  "imageCandidates",
  "audioOptions",
  "recorderState",
  "uploadWordImage",
  "findImages",
  "chooseNetworkImage",
  "wordNavUrl",
  "saveWordField",
  "refreshWord",
  "playAudio",
  "fetchAudioOptions",
  "startRecording",
  "chooseAudio",
  "stopRecording",
  "saveRecording",
  "fallbackLetter",
]);
</script>

<template>
  <section class="detail-layout">
    <WordMediaPanel
      :data="data"
      :image-candidates="imageCandidates"
      :fallback-letter="fallbackLetter"
      :upload-word-image="uploadWordImage"
      :find-images="findImages"
      :choose-network-image="chooseNetworkImage"
    />

    <WordDetailContentPanel
      :data="data"
      :word-edit="wordEdit"
      :audio-options="audioOptions"
      :recorder-state="recorderState"
      :word-nav-url="wordNavUrl"
      :save-word-field="saveWordField"
      :refresh-word="refreshWord"
      :play-audio="playAudio"
      :fetch-audio-options="fetchAudioOptions"
      :start-recording="startRecording"
      :choose-audio="chooseAudio"
      :stop-recording="stopRecording"
      :save-recording="saveRecording"
    />
  </section>
</template>
