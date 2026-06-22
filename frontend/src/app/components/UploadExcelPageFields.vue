<script setup>
import { setUploadFormFile } from "../forms/uploadExcelFormHandlers.js";
import { uploadExcelFormProps } from "../props/uploadExcelFormProps.js";

const props = defineProps(uploadExcelFormProps);

function chooseFile(event) {
  setUploadFormFile(props.uploadForm, event);
  props.uploadForm.notice = "";
}

function handleSubmit() {
  props.submitUpload();
}
</script>

<template>
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
      @change="chooseFile"
    >
  </label>
  <button type="button" :disabled="uploadForm.isUploading" @click="handleSubmit">
    {{ uploadForm.isUploading ? "上传中..." : "上传预览" }}
  </button>
  <p v-if="uploadForm.notice" class="notice">{{ uploadForm.notice }}</p>
</template>
