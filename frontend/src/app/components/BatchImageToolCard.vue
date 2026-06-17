<script setup>
defineProps({
  cards: {
    type: Array,
    required: true,
  },
  batchImageState: {
    type: Object,
    required: true,
  },
  submitBatchImages: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <article class="tool-card">
    <div>
      <p class="section-kicker">Images</p>
      <h2>批量上传图片</h2>
      <p>按序号或英文名自动匹配单词。</p>
    </div>
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
        @change="batchImageState.image_files = Array.from($event.target.files || [])"
      >
      <button type="button" @click="submitBatchImages">上传图片</button>
    </div>
    <p v-if="batchImageState.notice" class="notice">{{ batchImageState.notice }}</p>
  </article>
</template>
