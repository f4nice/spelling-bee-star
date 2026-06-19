<script setup>
import { wordDetailContentPanelProps } from "../props/wordDetailContentPanelProps.js";
import WordAudioPanel from "./WordAudioPanel.vue";
import WordDetailDefinitionPanel from "./WordDetailDefinitionPanel.vue";
import WordDetailHeading from "./WordDetailHeading.vue";
import WordStudyNav from "./WordStudyNav.vue";

defineProps(wordDetailContentPanelProps);
</script>

<template>
  <article class="panel detail-panel">
    <WordStudyNav :data="data" :word-nav-url="wordNavUrl" :play-audio="playAudio" />
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
