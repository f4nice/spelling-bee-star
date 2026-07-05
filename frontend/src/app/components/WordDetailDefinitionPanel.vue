<script setup>
import WordDefinitionList from "./WordDefinitionList.vue";

defineProps({
  data: {
    type: Object,
    required: true,
  },
  wordEdit: {
    type: Object,
    required: true,
  },
  saveWordField: {
    type: Function,
    required: true,
  },
  playAudio: {
    type: Function,
    required: true,
  },
  generateDefinitionAudio: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <WordDefinitionList
    :data="data"
    :word-edit="wordEdit"
    :save-word-field="saveWordField"
    :play-audio="playAudio"
    :generate-definition-audio="generateDefinitionAudio"
  />
</template>
