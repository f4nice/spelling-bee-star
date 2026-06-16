<script setup>
defineProps([
  "uploadForm",
  "uploadOptions",
  "submitUpload"
]);
</script>

<template>
  <section class="panel upload-panel">
    <div>
      <h1>导入 Excel</h1>
      <p>上传后会进入 Vue 预览页，可以选择行、列和单词列。</p>
    </div>
  </section>
  <form class="panel upload-form wide-form" @submit.prevent="submitUpload">
    <label>单词表名称 <input v-model="uploadForm.word_list_name" required></label>
    <label>
      已有单词表
      <select v-model="uploadForm.word_list_id">
        <option value="">新建单词表</option>
        <option v-for="list in uploadOptions.word_lists" :key="list.id" :value="list.id">{{ list.name }}</option>
      </select>
    </label>
    <label>Excel 文件 <input type="file" accept=".xlsx,.xlsm,.xltx,.xltm" required @change="uploadForm.file = $event.target.files[0]"></label>
    <button type="submit">上传预览</button>
  </form>
</template>
