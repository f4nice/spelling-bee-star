<script setup>
import BatchImageForm from "./BatchImageForm.vue";
import { batchImageToolProps } from "../props/batchImageToolProps.js";

defineProps(batchImageToolProps);
</script>

<template>
  <article class="tool-card">
    <div>
      <p class="section-kicker">Images</p>
      <h2>批量上传图片</h2>
      <p>按序号或英文名自动匹配单词。</p>
    </div>
    <BatchImageForm
      :cards="cards"
      :batch-image-state="batchImageState"
      :submit-batch-images="submitBatchImages"
    />
    <p v-if="batchImageState.notice" class="notice">{{ batchImageState.notice }}</p>
  </article>
</template>
