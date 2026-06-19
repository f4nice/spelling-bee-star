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
  <textarea v-model="book.text" placeholder="也可以直接粘贴一段英文正文" />
  <button class="wide-button" type="button" @click="analyzeBookText">分析文本</button>
</template>
