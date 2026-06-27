<script setup>
import BooklearnerDetailPanel from "./BooklearnerDetailPanel.vue";
import BooklearnerQuoteFeed from "./BooklearnerQuoteFeed.vue";

defineProps([
  "route",
  "book",
  "go",
  "analyzeBookQuery",
  "analyzeBookFile",
  "saveBookAnalysis",
  "createBookWordList",
]);
</script>

<template>
  <BooklearnerDetailPanel
    v-if="route.name === 'booklearnerDetail'"
    :route="route"
    :book="book"
    :go="go"
    :create-book-word-list="createBookWordList"
  />
  <BooklearnerQuoteFeed
    v-else-if="route.name !== 'booklearnerUpload'"
    :route="route"
    :book="book"
    :go="go"
  />
</template>
