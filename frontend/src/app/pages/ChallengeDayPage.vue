<script setup>
import ChallengeDayStats from "../components/ChallengeDayStats.vue";
import ChallengeDayWordCard from "../components/ChallengeDayWordCard.vue";

defineProps({
  data: {
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
});
</script>

<template>
  <ChallengeDayStats :correct="data.correct" :wrong="data.wrong" :go="go" />
  <section v-if="data.recovery_note" class="notice">
    {{ data.recovery_note }}
  </section>
  <section class="challenge-day-grid">
    <ChallengeDayWordCard
      v-for="item in data.words"
      :key="`${item.id}-${item.status}`"
      :item="item"
      :fallback-letter="fallbackLetter"
    />
  </section>
</template>
