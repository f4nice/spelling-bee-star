<script setup>
import WordListCard from "./WordListCard.vue";

defineProps({
  cards: {
    type: Array,
    required: true,
  },
  go: {
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
  <section class="word-grid home-list-grid">
    <WordListCard
      v-for="card in cards"
      :key="card.list.id"
      :card="card"
      :go="go"
      :fallback-letter="fallbackLetter"
    />
  </section>
</template>
