<script setup>
import WordEditableDefinitionItem from "./WordEditableDefinitionItem.vue";

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
    <dt>词性</dt>
    <dd>{{ data.word.part_of_speech || "暂无" }}</dd>

    <WordEditableDefinitionItem
      label="英文定义"
      field="english_definition"
      :word="data.word"
      :word-edit="wordEdit"
      :can-edit="data.can_edit"
      :save-word-field="saveWordField"
    />
    <WordEditableDefinitionItem
      label="中文定义"
      field="chinese_definition"
      :word="data.word"
      :word-edit="wordEdit"
      :can-edit="data.can_edit"
      :save-word-field="saveWordField"
    />
    <WordEditableDefinitionItem
      label="英文例句"
      field="english_example"
      :word="data.word"
      :word-edit="wordEdit"
      :can-edit="data.can_edit"
      :save-word-field="saveWordField"
    />

    <dt>来源</dt>
    <dd>{{ data.word.source || "暂无" }}</dd>
  </dl>
</template>
