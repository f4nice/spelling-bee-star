<script setup>
import BooklearnerFileSourceFields from "./BooklearnerFileSourceFields.vue";
import BooklearnerTextSourceFields from "./BooklearnerTextSourceFields.vue";

defineProps({
  book: {
    type: Object,
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
  <div class="form active" role="group" aria-label="按正文分析">
    <BooklearnerFileSourceFields :book="book" :analyze-book-file="analyzeBookFile" />
    <BooklearnerTextSourceFields :book="book" :analyze-book-text="analyzeBookText" />
  </div>
</template>
