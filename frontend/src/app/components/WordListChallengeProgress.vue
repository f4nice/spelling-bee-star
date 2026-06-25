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

const initialChallengeCount = computed(() => {
  const challenge = props.card.challenge || {};
  const total = Number(challenge.total || props.card.count || 1);
  const available = remainingCount.value > 0 ? remainingCount.value : total;
  return Math.min(20, Math.max(available, 1));
});

const challengeCount = ref(initialChallengeCount.value);

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
      <div
        class="challenge-round-badge"
        :class="{ 'is-complete': isChallengeComplete }"
        title="挑战次数"
      >
        <span class="challenge-crown" aria-hidden="true">♛</span>
        <strong>X{{ completedRoundCount }}</strong>
      </div>
      <label>
        <span>挑战几个</span>
        <input
          v-model.number="challengeCount"
          type="number"
          min="1"
          :max="Math.max(remainingCount || card.count || 1, 1)"
        >
      </label>
      <button class="challenge-button" type="submit">
        {{ isChallengeComplete ? "再次挑战" : "开始挑战" }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.challenge-card-actions {
  gap: 10px;
}

.challenge-round-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 40px;
  min-width: 72px;
  padding: 8px 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, #fff7d6, #fde68a);
  color: #92400e;
  font-weight: 900;
  box-shadow:
    inset 0 0 0 1px rgba(245, 158, 11, 0.28),
    0 10px 22px rgba(146, 64, 14, 0.12);
}

.challenge-round-badge strong {
  font-size: 18px;
  line-height: 1;
  letter-spacing: 0;
}

.challenge-crown {
  font-size: 18px;
  line-height: 1;
}

.challenge-round-badge.is-complete {
  background: linear-gradient(135deg, #fef3c7, #bbf7d0);
  color: #047857;
  box-shadow:
    inset 0 0 0 1px rgba(16, 185, 129, 0.25),
    0 10px 24px rgba(4, 120, 87, 0.14);
}
</style>
