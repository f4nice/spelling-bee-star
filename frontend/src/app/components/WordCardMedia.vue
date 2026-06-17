<script setup>
defineProps({
  word: {
    type: Object,
    required: true,
  },
  imageUrl: {
    type: String,
    default: "",
  },
  fallbackLetter: {
    type: String,
    required: true,
  },
});
</script>

<template>
  <img v-if="imageUrl" :src="imageUrl" :alt="word.word">
  <div v-else class="image-fallback">{{ fallbackLetter }}</div>
</template>
