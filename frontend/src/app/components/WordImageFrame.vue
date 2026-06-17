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
});
</script>

<template>
  <div class="word-image-frame">
    <img v-if="imageUrl" :src="imageUrl" :alt="word.word">
    <div v-else class="image-fallback">{{ word.word.slice(0, 1).toUpperCase() }}</div>
  </div>
</template>
