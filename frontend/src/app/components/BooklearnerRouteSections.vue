<script setup>
import BooklearnerDetailPanel from "./BooklearnerDetailPanel.vue";
import BooklearnerQuoteFeed from "./BooklearnerQuoteFeed.vue";
import BooklearnerScienceArticle from "./BooklearnerScienceArticle.vue";
import BooklearnerScienceDiscoveries from "./BooklearnerScienceDiscoveries.vue";

defineProps([
  "route",
  "book",
  "go",
  "analyzeBookQuery",
  "analyzeBookFile",
  "saveBookAnalysis",
  "createBookWordList",
  "loadScienceDiscoveries",
  "loadScienceArticle",
]);
</script>

<template>
  <BooklearnerScienceArticle
    v-if="route.name === 'booklearnerScience'"
    :route="route"
    :book="book"
    :go="go"
    :load-science-article="loadScienceArticle"
  />
  <BooklearnerDetailPanel
    v-else-if="route.name === 'booklearnerDetail'"
    :route="route"
    :book="book"
    :go="go"
    :create-book-word-list="createBookWordList"
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
