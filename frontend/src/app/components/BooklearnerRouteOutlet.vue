<script setup>
import BooklearnerPage from '../pages/BooklearnerPage.vue';

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <BooklearnerPage
    :route="ctx.route"
    :book="ctx.book"
    :go="ctx.go"
    :analyze-book-query="ctx.analyzeBookQuery"
    :analyze-book-file="ctx.analyzeBookFile"
    :save-book-analysis="ctx.saveBookAnalysis"
    :create-book-word-list="ctx.createBookWordList"
    :load-science-discoveries="ctx.loadScienceDiscoveries"
    :load-science-article="ctx.loadScienceArticle"
    :load-science-full-article="ctx.loadScienceFullArticle"
  />
</template>
