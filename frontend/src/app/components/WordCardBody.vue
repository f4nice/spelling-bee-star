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
      <span class="word-card-title-main">
        <strong>{{ word.word }}</strong>
        <span v-if="word.has_playable_audio" class="word-audio-badge" title="可朗读" aria-label="可朗读">🔊</span>
      </span>
      <WordChallengeStats :stats="word.challenge_stats" />
    </div>
    <p>{{ word.chinese_definition || word.english_definition || "等待补全" }}</p>
  </div>
</template>
