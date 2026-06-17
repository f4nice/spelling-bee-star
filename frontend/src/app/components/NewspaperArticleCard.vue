<script setup>
import NewspaperArticleMeta from "./NewspaperArticleMeta.vue";

defineProps({
  article: {
    type: Object,
    required: true,
  },
  lead: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["open"]);
</script>

<template>
  <button
    type="button"
    class="newspaper-card plain-card-button"
    :class="{ lead, 'has-image': article.image_url }"
    @click="$emit('open')"
  >
    <div v-if="article.image_url" class="newspaper-card-image">
      <img :src="article.image_url" :alt="article.title" loading="lazy">
    </div>
    <div class="newspaper-card-content">
      <NewspaperArticleMeta :article="article" />
      <h3>{{ article.title }}</h3>
      <p>{{ article.summary || article.excerpt }}</p>
      <small v-if="article.author">By {{ article.author }}</small>
    </div>
  </button>
</template>
