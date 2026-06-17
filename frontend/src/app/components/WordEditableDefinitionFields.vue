<script setup>
import WordEditableDefinitionItem from "./WordEditableDefinitionItem.vue";

defineProps({
  word: {
    type: Object,
    required: true,
  },
  wordEdit: {
    type: Object,
    required: true,
  },
  canEdit: {
    type: Boolean,
    default: false,
  },
  saveWordField: {
    type: Function,
    required: true,
  },
});

const fields = [
  { label: "英文定义", field: "english_definition" },
  { label: "中文定义", field: "chinese_definition" },
  { label: "英文例句", field: "english_example" },
];
</script>

<template>
  <WordEditableDefinitionItem
    v-for="item in fields"
    :key="item.field"
    :label="item.label"
    :field="item.field"
    :word="word"
    :word-edit="wordEdit"
    :can-edit="canEdit"
    :save-word-field="saveWordField"
  />
</template>
