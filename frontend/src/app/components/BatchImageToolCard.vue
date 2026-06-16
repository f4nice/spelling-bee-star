<script setup>
defineProps({
  cards: {
    type: Array,
    default: () => [],
  },
});
</script>

<template>
  <div class="lists-tool-card">
    <div class="lists-import-heading">
      <p class="section-kicker">Images</p>
      <h2>批量上传图片</h2>
      <p>按序号或英文名自动匹配单词。</p>
    </div>
    <form action="/lists/batch-images" method="post" enctype="multipart/form-data" class="home-upload-form batch-image-form">
      <select name="word_list_id" required>
        <option value="">选择单词表</option>
        <option v-for="card in cards" :key="card.list.id" :value="card.list.id">{{ card.list.name }}</option>
      </select>
      <input type="file" name="image_files" accept="image/*" multiple webkitdirectory directory required>
      <button type="submit">上传匹配</button>
    </form>
  </div>
</template>
