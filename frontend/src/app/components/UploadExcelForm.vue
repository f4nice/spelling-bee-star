<script setup>
import { computed } from "vue";

import { uploadExcelFormProps } from "../props/uploadExcelFormProps.js";

const props = defineProps(uploadExcelFormProps);

const formClasses = computed(() => [
  props.variant === "card" ? "home-upload-form" : "panel upload-form wide-form",
]);

function setUploadFile(event) {
  props.uploadForm.file = event.target.files[0];
}
</script>

<template>
  <div :class="formClasses" role="group" aria-label="导入单词">
    <label v-if="variant !== 'card'">
      单词表名称
      <input v-model="uploadForm.word_list_name" required>
    </label>
    <input
      v-else
      v-model="uploadForm.word_list_name"
      placeholder="新单词表名称"
    >

    <label v-if="variant !== 'card'">
      已有单词表
      <select v-model="uploadForm.word_list_id">
        <option value="">新建单词表</option>
        <option v-for="item in uploadOptions.word_lists" :key="item.id" :value="item.id">{{ item.name }}</option>
      </select>
    </label>
    <select v-else v-model="uploadForm.word_list_id">
      <option value="">新建单词表</option>
      <option v-for="item in uploadOptions.word_lists" :key="item.id" :value="item.id">{{ item.name }}</option>
    </select>

    <label v-if="variant !== 'card'">
      Excel 文件
      <input
        type="file"
        accept=".xlsx,.xlsm,.xltx,.xltm"
        required
        @change="setUploadFile"
      >
    </label>
    <input
      v-else
      type="file"
      accept=".xlsx,.xlsm,.xltx,.xltm"
      required
      @change="setUploadFile"
    >

    <button type="button" @click="submitUpload">上传预览</button>
  </div>
</template>
