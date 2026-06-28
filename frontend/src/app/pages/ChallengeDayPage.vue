<script setup>
import { computed, ref } from "vue";
import ChallengeDayStats from "../components/ChallengeDayStats.vue";
import ChallengeDayWordCard from "../components/ChallengeDayWordCard.vue";

const props = defineProps({
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

const activeFilter = ref("all");

const filteredWords = computed(() => {
  if (activeFilter.value === "all") return props.data.words || [];
  if (activeFilter.value === "wrong") return (props.data.words || []).filter((item) => item.was_wrong || item.status === "wrong");
  return (props.data.words || []).filter((item) => item.status === activeFilter.value);
});

const wrongChallengeCount = computed(
  () => props.data.wrong_challenge_count ?? props.data.correction_pending ?? props.data.wrong ?? 0,
);
const wrongChallengeUrl = computed(() => {
  if (!props.data.wrong_word_list_id || !wrongChallengeCount.value) return "";
  const params = new URLSearchParams({
    daily_count: String(wrongChallengeCount.value),
    start_count: "0",
    wrong_date: props.data.date,
    restart: "1",
  });
  return `/challenge/${props.data.wrong_word_list_id}?${params.toString()}`;
});

function setFilter(filter) {
  activeFilter.value = activeFilter.value === filter ? "all" : filter;
}
</script>

<template>
  <ChallengeDayStats
    :correct="data.correct"
    :wrong="data.wrong"
    :wrong-attempts="data.wrong_attempts"
    :corrected="data.corrected"
    :correction-pending="data.correction_pending"
    :active-filter="activeFilter"
    :wrong-challenge-url="wrongChallengeUrl"
    :wrong-challenge-count="wrongChallengeCount"
    :go="go"
    @filter="setFilter"
  />
  <section v-if="data.recovery_note" class="notice">
    {{ data.recovery_note }}
  </section>
  <section class="challenge-day-grid">
    <ChallengeDayWordCard
      v-for="item in filteredWords"
      :key="`${item.id}-${item.status}`"
      :item="item"
      :day="data.date"
      :fallback-letter="fallbackLetter"
    />
    <p v-if="!filteredWords.length" class="empty-state challenge-day-filter-empty">
      当前筛选没有单词。
    </p>
  </section>
</template>
