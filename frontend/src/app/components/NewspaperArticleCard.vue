<script setup>
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
      <div class="newspaper-card-meta">
        <span>{{ article.source }}</span>
        <span v-if="article.published">{{ article.published }}</span>
        <span v-if="article.category">{{ article.category }}</span>
      </div>
      <h3>{{ article.title }}</h3>
      <p>{{ article.summary || article.excerpt }}</p>
      <small v-if="article.author">By {{ article.author }}</small>
    </div>
  </button>
</template>
