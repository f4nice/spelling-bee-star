<script setup>
import { computed } from "vue";

import { setUploadFormFile } from "../forms/uploadExcelFormHandlers.js";
import { uploadExcelFormProps } from "../props/uploadExcelFormProps.js";

const props = defineProps(uploadExcelFormProps);

const selectedFileLabel = computed(() => (
  props.uploadForm.file?.name || "支持 .xlsx / .xlsm 文件"
));
</script>

<template>
  <input v-model="uploadForm.word_list_name" placeholder="新单词表名称">
  <select v-model="uploadForm.word_list_id">
    <option value="">新建单词表</option>
    <option v-for="item in uploadOptions.word_lists" :key="item.id" :value="item.id">{{ item.name }}</option>
  </select>
  <label class="excel-file-picker">
    <input
      type="file"
      accept=".xlsx,.xlsm,.xltx,.xltm"
      required
      @change="setUploadFormFile(uploadForm, $event)"
    >
    <span>选择 Excel</span>
    <small>{{ selectedFileLabel }}</small>
  </label>
  <button type="button" @click="submitUpload">上传预览</button>
</template>
