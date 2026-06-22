<script setup>
import { computed } from "vue";

import { batchImageToolProps } from "../props/batchImageToolProps.js";

const props = defineProps(batchImageToolProps);

const selectedImageLabel = computed(() => {
  const count = props.batchImageState.image_files.length;
  return count ? `已选择 ${count} 张图片` : "支持图片文件或文件夹";
});

function setImageFiles(event) {
  props.batchImageState.image_files = Array.from(event.target.files || []);
  props.batchImageState.notice = "";
}

function handleSubmit() {
  props.submitBatchImages();
}
</script>

<template>
  <div class="home-upload-form batch-image-form" role="group" aria-label="批量上传图片">
    <select v-model="batchImageState.word_list_id" required>
      <option value="">选择单词表</option>
      <option v-for="card in cards" :key="card.list.id" :value="card.list.id">{{ card.list.name }}</option>
    </select>
    <label class="batch-image-file-picker">
      <input
        type="file"
        accept="image/*"
        multiple
        webkitdirectory
        directory
        required
        @change="setImageFiles"
      >
      <span>选择图片</span>
      <small>{{ selectedImageLabel }}</small>
    </label>
    <button type="button" :disabled="batchImageState.isUploading" @click="handleSubmit">
      {{ batchImageState.isUploading ? "上传中..." : "上传图片" }}
    </button>
  </div>
</template>
