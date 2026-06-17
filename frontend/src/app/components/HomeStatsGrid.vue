<script setup>
import { computed } from "vue";
import { buildHomeStatCards } from "../homeStatCards.js";
import HomeStatCard from "./HomeStatCard.vue";

const props = defineProps({
  stats: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});

const cards = computed(() => buildHomeStatCards(props.stats));
</script>

<template>
  <section class="home-stats-grid">
    <HomeStatCard v-for="card in cards" :key="card.path" :card="card" :go="go" />
  </section>
</template>
