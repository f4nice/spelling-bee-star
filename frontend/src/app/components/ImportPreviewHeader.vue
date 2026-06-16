<script setup>
defineProps({
  preview: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="preview-heading">
    <div>
      <h1>导入预览</h1>
      <p>{{ preview.filename }} · {{ preview.rows.length }} 行 · {{ preview.columns.length }} 列</p>
    </div>
    <button class="ghost-button" type="button" @click="go('/upload')">重新选择文件</button>
  </div>
</template>
