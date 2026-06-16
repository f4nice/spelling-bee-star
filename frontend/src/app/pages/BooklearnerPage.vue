<script setup>
import BooklearnerDetailPanel from "../components/BooklearnerDetailPanel.vue";
import BooklearnerHero from "../components/BooklearnerHero.vue";
import BooklearnerHistoryGrid from "../components/BooklearnerHistoryGrid.vue";
import BooklearnerUploadWorkspace from "../components/BooklearnerUploadWorkspace.vue";

defineProps([
  "route",
  "book",
  "go",
  "analyzeBookQuery",
  "analyzeBookText",
  "analyzeBookFile",
  "saveBookAnalysis",
  "createBookWordList"
]);
</script>

<template>
  <section class="booklearner-page">
    <BooklearnerHero :route="route" :book="book" :go="go" />

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
  </section>
</template>
