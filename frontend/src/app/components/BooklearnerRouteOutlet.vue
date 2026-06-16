<script setup>
import BooklearnerPage from '../pages/BooklearnerPage.vue';

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <BooklearnerPage
    :route="ctx.route"
    :book="ctx.book"
    :go="ctx.go"
    :analyze-book-query="ctx.analyzeBookQuery"
    :analyze-book-text="ctx.analyzeBookText"
    :analyze-book-file="ctx.analyzeBookFile"
    :save-book-analysis="ctx.saveBookAnalysis"
    :create-book-word-list="ctx.createBookWordList"
  />
</template>
