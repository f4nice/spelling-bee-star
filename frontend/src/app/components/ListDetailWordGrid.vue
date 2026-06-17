<script setup>
import WordCard from "./WordCard.vue";

defineProps({
  data: {
    type: Object,
    required: true,
  },
  wordDetailUrl: {
    type: Function,
    required: true,
  },
  imageForWord: {
    type: Function,
    required: true,
  },
  fallbackLetter: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <section class="word-grid">
    <WordCard
      v-for="(word, index) in data.words"
      :key="word.id"
      :word="word"
      :index="index"
      :href="wordDetailUrl(word, data.word_list.id)"
      :image-url="imageForWord(word)"
      :fallback-letter="fallbackLetter(word)"
    />
  </section>
</template>
