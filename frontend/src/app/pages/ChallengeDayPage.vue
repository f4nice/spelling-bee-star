<script setup>
import ChallengeDayStats from "../components/ChallengeDayStats.vue";
import ChallengeDayWordCard from "../components/ChallengeDayWordCard.vue";

defineProps([
  "data",
  "go",
  "fallbackLetter"
]);
</script>

<template>
  <ChallengeDayStats :correct="data.correct" :wrong="data.wrong" :go="go" />
  <section class="challenge-day-grid">
    <ChallengeDayWordCard
      v-for="item in data.words"
      :key="`${item.id}-${item.status}`"
      :item="item"
      :fallback-letter="fallbackLetter"
    />
  </section>
</template>
