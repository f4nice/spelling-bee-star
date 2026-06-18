<script setup>
import BooklearnerSearchForm from "./BooklearnerSearchForm.vue";

defineProps({
  book: {
    type: Object,
    required: true,
  },
  analyzeBookQuery: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="form active" role="group" aria-label="按书名分析">
    <BooklearnerSearchForm :book="book" :analyze-book-query="analyzeBookQuery" />
  </div>
</template>
