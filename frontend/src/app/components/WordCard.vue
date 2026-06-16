<script setup>
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
  imageForWord: {
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
  <a class="word-card" :href="href">
    <span class="word-index-badge">#{{ index + 1 }}</span>
    <img v-if="imageForWord(word)" :src="word.image_url" :alt="word.word">
    <div v-else class="image-fallback">{{ fallbackLetter(word) }}</div>
    <div class="word-card-body">
      <div class="word-card-title">
        <strong>{{ word.word }}</strong>
        <span class="challenge-result-badges">
          <span class="challenge-result-badge is-correct">对 {{ word.challenge_stats.correct }}</span>
          <span class="challenge-result-badge is-wrong">错 {{ word.challenge_stats.wrong }}</span>
        </span>
      </div>
      <p>{{ word.chinese_definition || word.english_definition || '等待补全' }}</p>
    </div>
  </a>
</template>
