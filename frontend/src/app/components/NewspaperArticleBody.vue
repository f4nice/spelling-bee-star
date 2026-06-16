<script setup>
defineProps({
  article: {
    type: Object,
    required: true,
  },
  paragraphs: {
    type: Array,
    required: true,
  },
});
</script>

<template>
  <figure v-if="article.image_url" class="newspaper-article-image">
    <img :src="article.image_url" :alt="article.title">
  </figure>
  <p v-if="article.summary" class="newspaper-article-summary">{{ article.summary }}</p>
  <article class="newspaper-article-body">
    <p v-for="(paragraph, index) in paragraphs" :key="index">{{ paragraph }}</p>
  </article>
</template>
