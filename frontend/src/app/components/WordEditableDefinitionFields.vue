<script setup>
import { editableDefinitionFields } from "../wordDefinitionFields.js";
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

</script>

<template>
  <WordEditableDefinitionItem
    v-for="item in editableDefinitionFields"
    :key="item.field"
    :label="item.label"
    :field="item.field"
    :word="word"
    :word-edit="wordEdit"
    :can-edit="canEdit"
    :save-word-field="saveWordField"
  />
</template>
