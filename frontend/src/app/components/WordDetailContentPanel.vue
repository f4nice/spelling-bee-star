<script setup>
import { wordDetailContentPanelProps } from "../props/wordDetailContentPanelProps.js";
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
      :play-audio="playAudio"
    />

    <WordDetailDefinitionPanel
      :data="data"
      :word-edit="wordEdit"
      :save-word-field="saveWordField"
      :play-audio="playAudio"
      :generate-definition-audio="generateDefinitionAudio"
    />
  </article>
</template>
