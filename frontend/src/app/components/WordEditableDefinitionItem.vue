<script setup>
import WordEditableDefinitionValue from "./WordEditableDefinitionValue.vue";

defineProps({
  label: {
    type: String,
    required: true,
  },
  field: {
    type: String,
    required: true,
  },
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
  <dt>{{ label }}</dt>
  <dd>
    <WordEditableDefinitionValue
      :field="field"
      :word="word"
      :word-edit="wordEdit"
      :can-edit="canEdit"
      :save-word-field="saveWordField"
      :play-audio="playAudio"
      :generate-definition-audio="generateDefinitionAudio"
    />
  </dd>
</template>
