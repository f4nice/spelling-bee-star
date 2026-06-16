<script setup>
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

    <dt>英文定义</dt>
    <dd>
      <textarea v-if="data.can_edit" v-model="wordEdit.english_definition" @blur="saveWordField('english_definition')"></textarea>
      <span v-else>{{ data.word.english_definition || "暂无" }}</span>
    </dd>

    <dt>中文定义</dt>
    <dd>
      <textarea v-if="data.can_edit" v-model="wordEdit.chinese_definition" @blur="saveWordField('chinese_definition')"></textarea>
      <span v-else>{{ data.word.chinese_definition || "暂无" }}</span>
    </dd>

    <dt>英文例句</dt>
    <dd>
      <textarea v-if="data.can_edit" v-model="wordEdit.english_example" @blur="saveWordField('english_example')"></textarea>
      <span v-else>{{ data.word.english_example || "暂无" }}</span>
    </dd>

    <dt>来源</dt>
    <dd>{{ data.word.source || "暂无" }}</dd>
  </dl>
</template>
