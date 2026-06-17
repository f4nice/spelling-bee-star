<script setup>
defineProps({
  preview: {
    type: Object,
    required: true,
  },
  importForm: {
    type: Object,
    required: true,
  },
  changePreviewSheet: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <label>
    单词表名称
    <input v-model="importForm.word_list_name" required>
  </label>
  <label>
    Sheet
    <select
      v-if="preview.sheet_names?.length > 1"
      :value="preview.sheet_name"
      @change="changePreviewSheet($event.target.value)"
    >
      <option v-for="name in preview.sheet_names" :key="name" :value="name">{{ name }}</option>
    </select>
    <input v-else :value="preview.sheet_name || 'Sheet1'" disabled>
  </label>
</template>
