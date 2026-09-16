<script setup>
import WordEditableDefinitionFields from "./WordEditableDefinitionFields.vue";

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
  <dl class="definition-list">
    <WordEditableDefinitionFields
      :word="data.word"
      :word-edit="wordEdit"
      :can-edit="data.can_edit"
      :save-word-field="saveWordField"
      :play-audio="playAudio"
      :generate-definition-audio="generateDefinitionAudio"
    />
  </dl>
</template>
