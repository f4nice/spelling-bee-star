<script setup>
import NewspaperArticleBody from "../components/NewspaperArticleBody.vue";
import NewspaperArticleHeader from "../components/NewspaperArticleHeader.vue";

defineProps([
  "data",
  "go",
  "articleText"
]);
</script>

<template>
  <section class="panel newspaper-article">
    <NewspaperArticleHeader :section="data.section" :article="data.article" :go="go" />
    <NewspaperArticleBody :article="data.article" :paragraphs="articleText(data.article)" />
  </section>
</template>
