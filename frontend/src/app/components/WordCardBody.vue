<script setup>
import WordChallengeStats from "./WordChallengeStats.vue";

defineProps({
  word: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div class="word-card-body">
    <div class="word-card-title">
      <strong>{{ word.word }}</strong>
      <WordChallengeStats :stats="word.challenge_stats" />
    </div>
    <p>{{ word.chinese_definition || word.english_definition || "等待补全" }}</p>
  </div>
</template>
