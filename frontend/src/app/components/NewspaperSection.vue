<script setup>
import NewspaperArticleCard from "./NewspaperArticleCard.vue";
import NewspaperSectionHeader from "./NewspaperSectionHeader.vue";

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
    <NewspaperSectionHeader :section="section" />
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
