<script setup>
defineProps({
  book: {
    type: Object,
    required: true,
  },
  analyzeBookText: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <label>书籍正文</label>
  <textarea v-model="book.text" />
  <button class="wide-button" type="button" @click="analyzeBookText">分析文本</button>
</template>
