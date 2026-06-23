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
});
</script>

<template>
  <WordDefinitionList :data="data" :word-edit="wordEdit" :save-word-field="saveWordField" />
</template>
