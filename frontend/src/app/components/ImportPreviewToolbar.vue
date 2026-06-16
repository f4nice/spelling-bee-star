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
  setAllRows: {
    type: Function,
    required: true,
  },
  setAllColumns: {
    type: Function,
    required: true,
  },
  submitImport: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="import-toolbar">
    <label>单词表名称 <input v-model="importForm.word_list_name" required></label>
    <label>
      Sheet
      <select
        v-if="preview.sheet_names?.length > 1"
        :value="preview.sheet_name"
        @change="changePreviewSheet($event.target.value)"
      >
        <option v-for="sheet in preview.sheet_names" :key="sheet" :value="sheet">{{ sheet }}</option>
      </select>
      <input v-else :value="preview.sheet_name || 'Sheet1'" disabled>
    </label>
    <button type="button" class="secondary-button" @click="setAllRows(true)">全选行</button>
    <button type="button" class="secondary-button" @click="setAllRows(false)">取消行</button>
    <button type="button" class="secondary-button" @click="setAllColumns(true)">全选列</button>
    <button type="button" class="secondary-button" @click="setAllColumns(false)">取消列</button>
    <label>
      批量图片
      <input
        type="file"
        accept="image/*"
        multiple
        webkitdirectory
        directory
        @change="importForm.image_files = Array.from($event.target.files || [])"
      >
    </label>
    <button type="button" @click="submitImport">确认导入</button>
  </div>
</template>
