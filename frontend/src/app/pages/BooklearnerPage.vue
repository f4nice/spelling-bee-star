<script setup>
import BooklearnerHero from "../components/BooklearnerHero.vue";
import BooklearnerRouteSections from "../components/BooklearnerRouteSections.vue";

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

    <BooklearnerRouteSections
      :route="route"
      :book="book"
      :go="go"
      :analyze-book-query="analyzeBookQuery"
      :analyze-book-text="analyzeBookText"
      :analyze-book-file="analyzeBookFile"
      :save-book-analysis="saveBookAnalysis"
      :create-book-word-list="createBookWordList"
    />
  </section>
</template>
