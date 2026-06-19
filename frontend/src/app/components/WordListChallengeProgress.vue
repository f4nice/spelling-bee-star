<script setup>
import { computed, ref } from "vue";

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

const remainingCount = computed(() => {
  const challenge = props.card.challenge || {};
  const total = Number(challenge.total || props.card.count || 0);
  const completed = Number(challenge.completed || 0);
  return Math.max(total - completed, 0);
});

const challengeCount = ref(Math.min(20, Math.max(remainingCount.value, 1)));

const normalizedChallengeCount = computed(() => {
  const fallbackMax = Math.max(remainingCount.value || props.card.count || 1, 1);
  const max = Math.max(remainingCount.value || fallbackMax, 1);
  return Math.min(Math.max(Number(challengeCount.value) || 1, 1), max);
});

function startChallenge() {
  props.go(
    `/challenge/${props.card.list.id}?daily_count=${normalizedChallengeCount.value}&start_count=${props.card.challenge.completed}`,
  );
}
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
    <form class="challenge-start-form" @submit.prevent="startChallenge">
      <label>
        <span>挑战几个</span>
        <input
          v-model.number="challengeCount"
          type="number"
          min="1"
          :max="Math.max(remainingCount || card.count || 1, 1)"
        >
      </label>
      <button class="challenge-button" type="submit">开始挑战</button>
    </form>
  </div>
</template>
