<script setup>
import WordEditableDefinitionFields from "./WordEditableDefinitionFields.vue";
import WordStaticDefinitionItem from "./WordStaticDefinitionItem.vue";

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
  <dl class="definition-list">
    <WordStaticDefinitionItem label="词性" :value="data.word.part_of_speech" />
    <WordEditableDefinitionFields
      :word="data.word"
      :word-edit="wordEdit"
      :can-edit="data.can_edit"
      :save-word-field="saveWordField"
    />
  </dl>
</template>
