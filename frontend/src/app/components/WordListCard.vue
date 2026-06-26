<script setup>
import WordListCardBody from "./WordListCardBody.vue";
import WordListCardMedia from "./WordListCardMedia.vue";
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
      <WordListCardMedia :card="card" :fallback-letter="fallbackLetter" />
      <WordListCardBody :card="card" :show-challenge="showChallenge" />
    </button>

    <WordListChallengeProgress v-if="showChallenge" :card="card" :go="go" />
  </article>
</template>
