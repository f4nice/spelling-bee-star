<script setup>
defineProps({
  book: {
    type: Object,
    required: true,
  },
  analyzeBookFile: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <label>书名</label>
  <input v-model="book.title" placeholder="可选，默认使用文件名">
  <label>作者</label>
  <input v-model="book.author" placeholder="可选">
  <label>书籍文件</label>
  <label class="book-file-picker">
    <input
      type="file"
      accept=".txt,.epub,text/plain,application/epub+zip"
      @change="book.file = $event.target.files[0]"
    >
    <span>选择 TXT / EPUB</span>
    <small>{{ book.file?.name || "未选择文件" }}</small>
  </label>
  <button class="secondary-wide-button" type="button" @click="analyzeBookFile">分析文件</button>
</template>
