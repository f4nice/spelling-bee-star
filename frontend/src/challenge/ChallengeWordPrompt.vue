<script setup>
defineProps({
  word: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div class="challenge-word-prompt">
    <p class="section-kicker">当前单词</p>
    <h2>{{ word.chinese_definition || word.english_definition || "听音拼写" }}</h2>
    <p v-if="word.english_example">{{ word.english_example }}</p>
  </div>
</template>
