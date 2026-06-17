<script setup>
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
});
</script>

<template>
  <dt>{{ label }}</dt>
  <dd>
    <textarea v-if="canEdit" v-model="wordEdit[field]" @blur="saveWordField(field)"></textarea>
    <span v-else>{{ word[field] || "暂无" }}</span>
  </dd>
</template>
