<script setup>
import WordListChallengeProgress from "./WordListChallengeProgress.vue";

defineProps({
  card: {
    type: Object,
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
  showChallenge: {
    type: Boolean,
    default: false,
  },
});
</script>

<template>
  <article class="word-card list-card">
    <button class="list-card-link plain-card-button" type="button" @click="go(`/lists/${card.list.id}`)">
      <img v-if="card.cover_word?.image_url" :src="card.cover_word.image_url" :alt="card.list.name">
      <div v-else class="image-fallback">{{ fallbackLetter(card.cover_word) }}</div>
      <div class="word-card-body">
        <div class="word-card-title">
          <strong>{{ card.list.name }}</strong>
          <span class="status">{{ card.count }} 词</span>
        </div>
      </div>
    </button>

    <WordListChallengeProgress v-if="showChallenge" :card="card" :go="go" />
  </article>
</template>
