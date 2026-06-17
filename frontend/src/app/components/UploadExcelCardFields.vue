<script setup>
import { setUploadFormFile } from "../forms/uploadExcelFormHandlers.js";
import { uploadExcelFormProps } from "../props/uploadExcelFormProps.js";

defineProps(uploadExcelFormProps);
</script>

<template>
  <input v-model="uploadForm.word_list_name" placeholder="新单词表名称">
  <select v-model="uploadForm.word_list_id">
    <option value="">新建单词表</option>
    <option v-for="item in uploadOptions.word_lists" :key="item.id" :value="item.id">{{ item.name }}</option>
  </select>
  <input
    type="file"
    accept=".xlsx,.xlsm,.xltx,.xltm"
    required
    @change="setUploadFormFile(uploadForm, $event)"
  >
  <button type="button" @click="submitUpload">上传预览</button>
</template>
