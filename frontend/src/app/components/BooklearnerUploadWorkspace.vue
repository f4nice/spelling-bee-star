<script setup>
import BooklearnerAnalysisResult from "./BooklearnerAnalysisResult.vue";
import BooklearnerQueryPanel from "./BooklearnerQueryPanel.vue";

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
  <section class="book-workspace">
    <BooklearnerQueryPanel
      :book="book"
      :analyze-book-query="analyzeBookQuery"
      :analyze-book-text="analyzeBookText"
      :analyze-book-file="analyzeBookFile"
    />

    <BooklearnerAnalysisResult
      :book="book"
      :save-book-analysis="saveBookAnalysis"
      :create-book-word-list="createBookWordList"
    />
  </section>
</template>
