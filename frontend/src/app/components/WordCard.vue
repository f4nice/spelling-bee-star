<script setup>
import WordCardBody from "./WordCardBody.vue";
import WordCardMedia from "./WordCardMedia.vue";

defineProps({
  word: {
    type: Object,
    required: true,
  },
  index: {
    type: Number,
    required: true,
  },
  href: {
    type: String,
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
  <a class="word-card" :href="href">
    <span class="word-index-badge">#{{ index + 1 }}</span>
    <WordCardMedia :word="word" :image-url="imageUrl" :fallback-letter="fallbackLetter" />
    <WordCardBody :word="word" />
  </a>
</template>
