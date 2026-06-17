<script setup>
defineProps({
  stats: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <span class="challenge-result-badges">
    <span class="challenge-result-badge is-correct">对 {{ stats.correct }}</span>
    <span class="challenge-result-badge is-wrong">错 {{ stats.wrong }}</span>
  </span>
</template>
