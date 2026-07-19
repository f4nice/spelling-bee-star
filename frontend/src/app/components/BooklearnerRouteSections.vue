<script setup>
import { defineAsyncComponent } from "vue";

const BooklearnerDetailPanel = defineAsyncComponent(() => import("./BooklearnerDetailPanel.vue"));
const BooklearnerQuoteFeed = defineAsyncComponent(() => import("./BooklearnerQuoteFeed.vue"));

defineProps([
  "route",
  "book",
  "go",
  "analyzeBookQuery",
  "analyzeBookFile",
  "saveBookAnalysis",
  "createBookWordList",
  "uploadBookCover",
  "generateBookAiCover",
]);
</script>

<template>
  <BooklearnerDetailPanel
    v-if="route.name === 'booklearnerDetail'"
    :route="route"
    :book="book"
    :go="go"
    :create-book-word-list="createBookWordList"
    :upload-book-cover="uploadBookCover"
    :generate-book-ai-cover="generateBookAiCover"
  />
  <template v-else-if="route.name !== 'booklearnerUpload'">
    <BooklearnerQuoteFeed
      :route="route"
      :book="book"
      :go="go"
    />
  </template>
</template>
