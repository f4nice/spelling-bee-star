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
  return (props.data.words || []).filter((item) => item.status === activeFilter.value);
});

function setFilter(filter) {
  activeFilter.value = activeFilter.value === filter ? "all" : filter;
}
</script>

<template>
  <ChallengeDayStats
    :correct="data.correct"
    :wrong="data.wrong"
    :active-filter="activeFilter"
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
      :fallback-letter="fallbackLetter"
    />
    <p v-if="!filteredWords.length" class="empty-state challenge-day-filter-empty">
      当前筛选没有单词。
    </p>
  </section>
</template>
