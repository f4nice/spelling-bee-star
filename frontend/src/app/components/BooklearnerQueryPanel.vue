<script setup>
defineProps({
  book: {
    type: Object,
    required: true,
  },
  analyzeBookQuery: {
    type: Function,
    required: true,
  },
  analyzeBookText: {
    type: Function,
    required: true,
  },
  analyzeBookFile: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <aside class="query-panel">
    <form class="form active" @submit.prevent="analyzeBookQuery">
      <label>书名或作者</label>
      <div class="input-row">
        <input v-model="book.query" placeholder="Pride and Prejudice">
        <button type="submit">分析</button>
      </div>
    </form>

    <form class="form active" @submit.prevent="analyzeBookText">
      <label>书名</label>
      <input v-model="book.title">
      <label>作者</label>
      <input v-model="book.author">
      <label>书籍文件</label>
      <input type="file" accept=".txt,.epub,text/plain,application/epub+zip" @change="book.file = $event.target.files[0]">
      <button class="secondary-wide-button" type="button" @click="analyzeBookFile">分析文件</button>
      <label>书籍正文</label>
      <textarea v-model="book.text"></textarea>
      <button class="wide-button" type="submit">分析文本</button>
    </form>

    <div v-if="book.notice" class="notice">{{ book.notice }}</div>
  </aside>
</template>
