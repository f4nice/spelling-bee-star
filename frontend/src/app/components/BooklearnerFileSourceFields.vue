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
  <input v-model="book.title">
  <label>作者</label>
  <input v-model="book.author">
  <label>书籍文件</label>
  <input
    type="file"
    accept=".txt,.epub,text/plain,application/epub+zip"
    @change="book.file = $event.target.files[0]"
  >
  <button class="secondary-wide-button" type="button" @click="analyzeBookFile">分析文件</button>
</template>
