<script setup>
import { booklearnerUploadWorkspaceProps } from "../props/booklearnerUploadWorkspaceProps.js";
import BooklearnerAnalysisResult from "./BooklearnerAnalysisResult.vue";
import BooklearnerQueryPanel from "./BooklearnerQueryPanel.vue";

defineProps(booklearnerUploadWorkspaceProps);
</script>

<template>
  <section class="book-workspace">
    <BooklearnerQueryPanel
      :book="book"
      :analyze-book-query="analyzeBookQuery"
      :analyze-book-text="analyzeBookText"
      :analyze-book-file="analyzeBookFile"
    />

    <BooklearnerAnalysisResult
      :book="book"
      :save-book-analysis="saveBookAnalysis"
      :create-book-word-list="createBookWordList"
    />
  </section>
</template>
