<script setup>
import { computed } from "vue";
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

const cards = computed(() => [
  {
    label: "我的单词表",
    value: props.stats.word_lists,
    detail: `${props.stats.words} 个单词`,
    path: "/lists",
  },
  {
    label: "英文小报",
    value: "Today",
    detail: "China Daily 今日泛读",
    path: "/newspaper",
  },
  {
    label: "好词好句",
    value: "Books",
    detail: "书摘与难点词",
    path: "/booklearner",
  },
  {
    label: "我的生词本",
    value: props.stats.wrong_words,
    detail: `今日 ${props.stats.today_wrong_count} 个`,
    path: "/wrong-words",
  },
]);
</script>

<template>
  <section class="home-stats-grid">
    <HomeStatCard v-for="card in cards" :key="card.path" :card="card" :go="go" />
  </section>
</template>
