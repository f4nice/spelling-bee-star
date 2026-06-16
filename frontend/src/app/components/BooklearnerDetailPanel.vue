<script setup>
defineProps({
  book: {
    type: Object,
    required: true,
  },
  createBookWordList: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <section v-if="book.result" class="panel">
    <h2>{{ book.result.book?.title || book.result.title || '书籍详情' }}</h2>
    <button type="button" class="secondary-button" @click="createBookWordList">生成单词表</button>
    <pre class="booklearner-json">{{ JSON.stringify(book.result, null, 2) }}</pre>
  </section>
</template>
