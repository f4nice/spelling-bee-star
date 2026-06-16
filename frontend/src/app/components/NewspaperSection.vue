<script setup>
import NewspaperArticleCard from "./NewspaperArticleCard.vue";

defineProps({
  section: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <article class="panel newspaper-section">
    <div class="newspaper-section-head">
      <h2>{{ section.name }}</h2>
      <span>{{ section.articles?.length || 0 }} articles</span>
    </div>
    <p v-if="section.error" class="newspaper-error">{{ section.error }}</p>
    <div v-else class="newspaper-list">
      <NewspaperArticleCard
        v-for="(article, index) in section.articles"
        :key="article.link || article.title"
        :article="article"
        :lead="index === 0"
        @open="go(`/newspaper/${section.key}/${index}`)"
      />
    </div>
  </article>
</template>
