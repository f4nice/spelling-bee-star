<script setup>
import HomeChallengeCalendar from "../components/HomeChallengeCalendar.vue";
import HomeFeaturedLists from "../components/HomeFeaturedLists.vue";
import HomeStatsGrid from "../components/HomeStatsGrid.vue";

defineProps([
  "data",
  "go",
  "fallbackLetter"
]);
</script>

<template>
  <HomeStatsGrid :stats="data.stats" :go="go" />
  <HomeChallengeCalendar :calendar="data.calendar" :go="go" />
  <HomeFeaturedLists :cards="data.featured_cards" :go="go" :fallback-letter="fallbackLetter" />
</template>
