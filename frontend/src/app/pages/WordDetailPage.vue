<script setup>
import WordAudioPanel from "../components/WordAudioPanel.vue";
import WordDefinitionList from "../components/WordDefinitionList.vue";
import WordDetailHeading from "../components/WordDetailHeading.vue";
import WordMediaPanel from "../components/WordMediaPanel.vue";
import WordStudyNav from "../components/WordStudyNav.vue";

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
  "fallbackLetter"
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

      <WordDefinitionList :data="data" :word-edit="wordEdit" :save-word-field="saveWordField" />
      <div v-if="data.word.enrichment_error" class="error-box">{{ data.word.enrichment_error }}</div>
    </article>
  </section>
</template>
