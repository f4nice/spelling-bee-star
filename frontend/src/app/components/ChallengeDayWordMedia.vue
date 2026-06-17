<script setup>
defineProps({
  item: {
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
  <img v-if="item.image_url" :src="item.image_url" :alt="item.word" loading="lazy">
  <div v-else class="image-fallback">{{ fallbackLetter(item) }}</div>
</template>
