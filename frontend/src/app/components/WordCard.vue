<script setup>
import WordCardMedia from "./WordCardMedia.vue";
import WordChallengeStats from "./WordChallengeStats.vue";

defineProps({
  word: {
    type: Object,
    required: true,
  },
  index: {
    type: Number,
    required: true,
  },
  href: {
    type: String,
    required: true,
  },
  imageUrl: {
    type: String,
    default: "",
  },
  fallbackLetter: {
    type: String,
    required: true,
  },
});
</script>

<template>
  <a class="word-card" :href="href">
    <span class="word-index-badge">#{{ index + 1 }}</span>
    <WordCardMedia :word="word" :image-url="imageUrl" :fallback-letter="fallbackLetter" />
    <div class="word-card-body">
      <div class="word-card-title">
        <strong>{{ word.word }}</strong>
        <WordChallengeStats :stats="word.challenge_stats" />
      </div>
      <p>{{ word.chinese_definition || word.english_definition || "等待补全" }}</p>
    </div>
  </a>
</template>
