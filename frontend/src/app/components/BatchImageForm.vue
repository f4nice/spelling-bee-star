<script setup>
import { computed } from "vue";

import { batchImageToolProps } from "../props/batchImageToolProps.js";

const props = defineProps(batchImageToolProps);

const selectedImageLabel = computed(() => {
  const count = props.batchImageState.image_files.length;
  return count ? `已选择 ${count} 张图片` : "支持图片文件或文件夹";
});

function setImageFiles(event) {
  const selected = Array.from(event.target.files || []);
  const existing = props.batchImageState.image_files || [];
  const seen = new Set(existing.map((file) => `${file.name}:${file.size}:${file.lastModified}`));
  props.batchImageState.image_files = [
    ...existing,
    ...selected.filter((file) => {
      const key = `${file.name}:${file.size}:${file.lastModified}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }),
  ];
  props.batchImageState.notice = "";
  event.target.value = "";
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
        required
        @change="setImageFiles"
      >
      <span>选择图片文件</span>
      <small>{{ selectedImageLabel }}</small>
    </label>
    <label class="batch-image-file-picker">
      <input
        type="file"
        accept="image/*"
        multiple
        webkitdirectory
        directory
        @change="setImageFiles"
      >
      <span>选择图片文件夹</span>
      <small>{{ selectedImageLabel }}</small>
    </label>
    <button type="button" :disabled="batchImageState.isUploading" @click="handleSubmit">
      {{ batchImageState.isUploading ? "上传中..." : "上传图片" }}
    </button>
  </div>
</template>
