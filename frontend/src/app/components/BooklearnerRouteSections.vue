<script setup>
import BooklearnerDetailPanel from "./BooklearnerDetailPanel.vue";
import BooklearnerHistoryGrid from "./BooklearnerHistoryGrid.vue";

defineProps([
  "route",
  "book",
  "go",
  "analyzeBookQuery",
  "analyzeBookText",
  "analyzeBookFile",
  "saveBookAnalysis",
  "createBookWordList",
]);
</script>

<template>
  <BooklearnerDetailPanel
    v-if="route.name === 'booklearnerDetail'"
    :book="book"
    :create-book-word-list="createBookWordList"
  />
  <BooklearnerHistoryGrid v-if="route.name !== 'booklearnerUpload'" :book="book" :go="go" />
</template>
