<script setup>
import { defineAsyncComponent } from "vue";

const BooklearnerDetailPanel = defineAsyncComponent(() => import("./BooklearnerDetailPanel.vue"));
const BooklearnerQuoteFeed = defineAsyncComponent(() => import("./BooklearnerQuoteFeed.vue"));
const BooklearnerScienceArticle = defineAsyncComponent(() => import("./BooklearnerScienceArticle.vue"));
const BooklearnerScienceDiscoveries = defineAsyncComponent(() => import("./BooklearnerScienceDiscoveries.vue"));

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
  "loadScienceDiscoveries",
  "loadScienceArticle",
  "loadScienceFullArticle",
]);
</script>

<template>
  <BooklearnerScienceArticle
    v-if="route.name === 'booklearnerScience'"
    :route="route"
    :book="book"
    :go="go"
    :load-science-article="loadScienceArticle"
    :load-science-full-article="loadScienceFullArticle"
  />
  <BooklearnerScienceDiscoveries
    v-else-if="route.name === 'booklearnerScienceHome'"
    :book="book"
    :go="go"
    :load-science-discoveries="loadScienceDiscoveries"
  />
  <BooklearnerDetailPanel
    v-else-if="route.name === 'booklearnerDetail'"
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
    <BooklearnerScienceDiscoveries
      v-if="route.name === 'booklearner'"
      :book="book"
      :go="go"
      :load-science-discoveries="loadScienceDiscoveries"
    />
  </template>
</template>
