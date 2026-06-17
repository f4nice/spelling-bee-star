<script setup>
import { batchImageToolProps } from "../props/batchImageToolProps.js";

const props = defineProps(batchImageToolProps);

function setImageFiles(event) {
  props.batchImageState.image_files = Array.from(event.target.files || []);
}
</script>

<template>
  <div class="home-upload-form batch-image-form" role="group" aria-label="批量上传图片">
    <select v-model="batchImageState.word_list_id" required>
      <option value="">选择单词表</option>
      <option v-for="card in cards" :key="card.list.id" :value="card.list.id">{{ card.list.name }}</option>
    </select>
    <input
      type="file"
      accept="image/*"
      multiple
      webkitdirectory
      directory
      required
      @change="setImageFiles"
    >
    <button type="button" @click="submitBatchImages">上传图片</button>
  </div>
</template>
