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
    <span v-if="article.published">{{ article.published }}</span>
    <span v-if="article.category">{{ article.category }}</span>
    <span v-if="article.author">By {{ article.author }}</span>
  </div>
</template>
