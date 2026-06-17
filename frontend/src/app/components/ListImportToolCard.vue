<script setup>
defineProps({
  uploadOptions: {
    type: Object,
    required: true,
  },
  uploadForm: {
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
  <article class="tool-card">
    <div>
      <p class="section-kicker">Excel</p>
      <h2>导入单词</h2>
      <p>上传 Excel 后进入导入预览页。</p>
    </div>
    <div class="home-upload-form" role="group" aria-label="导入单词">
      <input v-model="uploadForm.word_list_name" placeholder="新单词表名称">
      <select v-model="uploadForm.word_list_id">
        <option value="">新建单词表</option>
        <option v-for="item in uploadOptions.word_lists" :key="item.id" :value="item.id">{{ item.name }}</option>
      </select>
      <input
        type="file"
        accept=".xlsx,.xlsm,.xltx,.xltm"
        required
        @change="uploadForm.file = $event.target.files[0]"
      >
      <button type="button" @click="submitUpload">上传预览</button>
    </div>
  </article>
</template>
