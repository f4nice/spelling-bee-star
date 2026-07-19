<script setup>
import { defineAsyncComponent } from "vue";

const BooklearnerPage = defineAsyncComponent(() => import("../pages/BooklearnerPage.vue"));

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
    :upload-book-cover="ctx.uploadBookCover"
    :generate-book-ai-cover="ctx.generateBookAiCover"
  />
</template>
