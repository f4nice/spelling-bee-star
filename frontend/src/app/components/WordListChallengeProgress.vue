<script setup>
defineProps({
  card: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="challenge-card-actions">
    <div class="mini-progress">
      <span>{{ card.challenge.completed }} / {{ card.challenge.total }}</span>
      <div><i :style="{ width: `${card.challenge.percent}%` }"></i></div>
    </div>
    <button
      class="challenge-button"
      type="button"
      @click="go(`/challenge/${card.list.id}?daily_count=20&start_count=${card.challenge.completed}`)"
    >
      开始挑战
    </button>
  </div>
</template>
