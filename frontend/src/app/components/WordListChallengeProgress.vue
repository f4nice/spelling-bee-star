<script setup>
import { computed } from "vue";

const props = defineProps({
  card: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});

const progressText = computed(() => {
  const challenge = props.card.challenge || {};
  return `${challenge.completed || 0} / ${challenge.total || props.card.count || 0}`;
});
</script>

<template>
  <div class="challenge-card-actions">
    <div class="mini-progress">
      <div class="mini-progress-heading">
        <span>挑战进度</span>
        <strong>{{ progressText }}</strong>
      </div>
      <div><i :style="{ width: `${card.challenge.percent}%` }"></i></div>
      <p>
        已挑战 {{ card.challenge.completed }} 个，
        共 {{ card.challenge.total }} 个
      </p>
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
