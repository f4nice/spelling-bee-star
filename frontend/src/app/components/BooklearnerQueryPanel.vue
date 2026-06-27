<script setup>
import BooklearnerSearchPanel from "./BooklearnerSearchPanel.vue";
import BooklearnerTextSourcePanel from "./BooklearnerTextSourcePanel.vue";

defineProps({
  book: {
    type: Object,
    required: true,
  },
  analyzeBookQuery: {
    type: Function,
    required: true,
  },
  analyzeBookFile: {
    type: Function,
    required: true,
  },
  saveBookAnalysis: {
    type: Function,
    required: true,
  },
  createBookWordList: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <aside class="query-panel">
    <BooklearnerSearchPanel :book="book" :analyze-book-query="analyzeBookQuery" />
    <BooklearnerTextSourcePanel
      :book="book"
      :analyze-book-file="analyzeBookFile"
      :save-book-analysis="saveBookAnalysis"
      :create-book-word-list="createBookWordList"
    />

    <div v-if="book.notice" class="notice">{{ book.notice }}</div>
  </aside>
</template>
