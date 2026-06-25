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

const remainingCount = computed(() => {
  const challenge = props.card.challenge || {};
  const total = Number(challenge.total || props.card.count || 0);
  const completed = Number(challenge.completed || 0);
  return Math.max(total - completed, 0);
});

const challengeCount = ref(Math.min(20, Math.max(remainingCount.value, 1)));

const isChallengeComplete = computed(() => {
  const challenge = props.card.challenge || {};
  const total = Number(challenge.total || props.card.count || 0);
  return total > 0 && remainingCount.value <= 0;
});

const completedRoundCount = computed(() => (isChallengeComplete.value ? 1 : 0));

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
    <div
      class="challenge-round-badge"
      :class="{ 'is-complete': isChallengeComplete }"
    >
      <span>挑战次数</span>
      <strong>{{ completedRoundCount }}</strong>
      <span>次</span>
    </div>
    <div v-if="isChallengeComplete" class="challenge-complete-mini">
      已完成
    </div>
    <form v-else class="challenge-start-form" @submit.prevent="startChallenge">
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

<style scoped>
.challenge-card-actions {
  gap: 10px;
}

.challenge-round-badge {
  display: inline-flex;
  align-items: baseline;
  justify-content: center;
  gap: 4px;
  min-height: 40px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff7ed;
  color: #9a3412;
  font-weight: 800;
  box-shadow: inset 0 0 0 1px rgba(251, 146, 60, 0.25);
}

.challenge-round-badge strong {
  font-size: 22px;
  line-height: 1;
}

.challenge-round-badge.is-complete {
  background: #ecfdf5;
  color: #047857;
  box-shadow: inset 0 0 0 1px rgba(16, 185, 129, 0.28);
}

.challenge-complete-mini {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  width: 100%;
  border-radius: 8px;
  background: #ecfdf5;
  color: #047857;
  font-weight: 800;
}
</style>
