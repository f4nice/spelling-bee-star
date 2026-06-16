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
  <div class="lists-tool-card">
    <div class="lists-import-heading">
      <p class="section-kicker">Import</p>
      <h2>新增单词表</h2>
    </div>
    <form class="home-upload-form lists-import-form" @submit.prevent="submitUpload">
      <input v-model="uploadForm.word_list_name" type="text" placeholder="单词表名称" required>
      <select v-model="uploadForm.word_list_id">
        <option value="">新建单词表</option>
        <option v-for="list in uploadOptions.word_lists" :key="list.id" :value="list.id">{{ list.name }}</option>
      </select>
      <input type="file" accept=".xlsx,.xlsm,.xltx,.xltm" required @change="uploadForm.file = $event.target.files[0]">
      <button type="submit">上传预览</button>
    </form>
  </div>
</template>
