<script setup>
import WordListCard from './WordListCard.vue';

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
  <section class="home-section-head">
    <div>
      <p class="section-kicker">Lists</p>
      <h2>我的单词表</h2>
    </div>
    <button class="ghost-button" type="button" @click="go('/lists')">全部单词表</button>
  </section>

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
