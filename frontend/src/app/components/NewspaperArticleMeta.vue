<script setup>
defineProps({
  article: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div class="newspaper-card-meta">
    <span>{{ article.source }}</span>
    <span v-if="article.published">{{ article.published }}</span>
    <span v-if="article.category">{{ article.category }}</span>
  </div>
</template>
