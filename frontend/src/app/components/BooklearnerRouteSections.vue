<script setup>
import BooklearnerDetailPanel from "./BooklearnerDetailPanel.vue";
import BooklearnerHistoryGrid from "./BooklearnerHistoryGrid.vue";
import BooklearnerUploadWorkspace from "./BooklearnerUploadWorkspace.vue";

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
  <BooklearnerUploadWorkspace
    v-if="route.name === 'booklearnerUpload'"
    :book="book"
    :analyze-book-query="analyzeBookQuery"
    :analyze-book-text="analyzeBookText"
    :analyze-book-file="analyzeBookFile"
    :save-book-analysis="saveBookAnalysis"
    :create-book-word-list="createBookWordList"
  />

  <BooklearnerHistoryGrid v-if="route.name !== 'booklearnerUpload'" :book="book" :go="go" />
  <BooklearnerDetailPanel
    v-if="route.name === 'booklearnerDetail'"
    :book="book"
    :create-book-word-list="createBookWordList"
  />
</template>
