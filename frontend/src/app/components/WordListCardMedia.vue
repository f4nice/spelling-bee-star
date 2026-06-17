<script setup>
defineProps({
  card: {
    type: Object,
    required: true,
  },
  fallbackLetter: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <img v-if="card.cover_word?.image_url" :src="card.cover_word.image_url" :alt="card.list.name">
  <div v-else class="image-fallback">{{ fallbackLetter(card.cover_word) }}</div>
</template>
