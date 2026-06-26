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
const crownImageUrl = "/static/icons/challenge-crown.png";

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
        <img class="challenge-crown-image" :src="crownImageUrl" alt="" aria-hidden="true">
      </div>
      <div class="challenge-start-fields">
        <div class="challenge-round-count">
          <span>挑战次数</span>
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
      </div>
    </form>
  </div>
</template>

<style scoped>
.challenge-card-actions {
  gap: 10px;
}

.challenge-start-form {
  width: 100%;
  grid-template-columns: 88px minmax(0, 1fr);
  align-items: center;
  gap: 14px;
}

.challenge-start-fields {
  display: grid;
  grid-template-columns: minmax(54px, 1fr) auto;
  align-items: end;
  gap: 8px;
}

.challenge-round-count {
  grid-column: 1 / -1;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  color: #475569;
  font-weight: 800;
}

.challenge-round-count span {
  font-size: 13px;
}

.challenge-round-count strong {
  color: #8a4b05;
  font-size: 20px;
  line-height: 1;
  letter-spacing: 0;
}

.challenge-round-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  justify-self: start;
  width: 80px;
  height: 80px;
  padding: 0;
  border-radius: 20px;
  background:
    radial-gradient(circle at 28% 22%, rgba(255, 255, 255, 0.85), transparent 28%),
    linear-gradient(135deg, #fff3b0 0%, #f7c948 48%, #c98712 100%);
  color: #6f3f00;
  font-weight: 900;
  box-shadow:
    inset 0 0 0 1px rgba(180, 83, 9, 0.2),
    0 12px 24px rgba(180, 83, 9, 0.22);
  overflow: hidden;
}

.challenge-crown-image {
  width: 80px;
  height: 80px;
  display: block;
  object-fit: cover;
  border-radius: 18px;
  mix-blend-mode: multiply;
  filter: drop-shadow(0 3px 5px rgba(120, 53, 15, 0.24));
}

.challenge-round-badge.is-complete {
  background:
    radial-gradient(circle at 28% 22%, rgba(255, 255, 255, 0.86), transparent 28%),
    linear-gradient(135deg, #fff7ad 0%, #facc15 46%, #16a34a 100%);
  color: #064e3b;
  box-shadow:
    inset 0 0 0 1px rgba(16, 185, 129, 0.22),
    0 12px 26px rgba(4, 120, 87, 0.18);
}

@media (max-width: 720px) {
  .challenge-start-form,
  .challenge-start-fields {
    grid-template-columns: 1fr;
  }
}
</style>
