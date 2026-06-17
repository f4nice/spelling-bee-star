<script setup>
defineProps({
  uploadForm: {
    type: Object,
    required: true,
  },
  uploadOptions: {
    type: Object,
    required: true,
  },
  submitUpload: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <section class="panel upload-panel">
    <div>
      <h1>导入 Excel</h1>
      <p>上传后会进入预览页，可以选择行、列和单词列。</p>
    </div>
  </section>

  <section class="panel upload-form wide-form" role="group" aria-label="导入 Excel">
    <label>
      单词表名称
      <input v-model="uploadForm.word_list_name" required>
    </label>
    <label>
      已有单词表
      <select v-model="uploadForm.word_list_id">
        <option value="">新建单词表</option>
        <option v-for="item in uploadOptions.word_lists" :key="item.id" :value="item.id">{{ item.name }}</option>
      </select>
    </label>
    <label>
      Excel 文件
      <input
        type="file"
        accept=".xlsx,.xlsm,.xltx,.xltm"
        required
        @change="uploadForm.file = $event.target.files[0]"
      >
    </label>
    <button type="button" @click="submitUpload">上传预览</button>
  </section>
</template>
