<script setup>
import { computed, ref, watch } from "vue";

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

const totalCount = computed(() => {
  const challenge = props.card.challenge || {};
  return Math.max(Number(challenge.total || props.card.count || 1), 1);
});

const maxChallengeCount = computed(() => Math.min(totalCount.value, 500));

const initialChallengeCount = computed(() => {
  const remaining = remainingCount.value > 0 ? remainingCount.value : maxChallengeCount.value;
  return Math.min(remaining, maxChallengeCount.value);
});

const challengeCount = ref(initialChallengeCount.value);

watch(
  initialChallengeCount,
  (value) => {
    challengeCount.value = value;
  },
  { immediate: true }
);

const isChallengeComplete = computed(() => {
  const challenge = props.card.challenge || {};
  const total = Number(challenge.total || props.card.count || 0);
  return total > 0 && remainingCount.value <= 0;
});

const hasCompletedRounds = computed(() => Number(props.card.challenge?.completed_rounds || 0) > 0);

const normalizedChallengeCount = computed(() => {
  return Math.min(Math.max(Number(challengeCount.value) || 1, 1), maxChallengeCount.value);
});

function startChallenge() {
  const params = new URLSearchParams({
    daily_count: String(normalizedChallengeCount.value),
    start_count: isChallengeComplete.value ? "0" : String(props.card.challenge.completed || 0),
  });
  if (isChallengeComplete.value) params.set("restart", "1");
  props.go(`/challenge/${props.card.list.id}?${params.toString()}`);
}
</script>

<template>
  <div class="challenge-card-actions">
    <form class="challenge-start-form" @submit.prevent="startChallenge">
      <label>
        <span>挑战几个</span>
        <input
          v-model.number="challengeCount"
          type="number"
          min="1"
          :max="maxChallengeCount"
        >
      </label>
      <button class="challenge-button" type="submit">
        {{ hasCompletedRounds ? "再次挑战" : "开始挑战" }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.challenge-card-actions {
  gap: 0;
  padding: 14px;
}

.challenge-start-form {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 10px;
}

@media (max-width: 720px) {
  .challenge-start-form {
    grid-template-columns: 1fr;
  }
}
</style>
