<script setup>
defineProps({
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
  <textarea v-if="canEdit" v-model="wordEdit[field]" @blur="saveWordField(field)"></textarea>
  <span v-else>{{ word[field] || "暂无" }}</span>
</template>
