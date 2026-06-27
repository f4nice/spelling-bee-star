<script setup>
import { computed } from "vue";

const props = defineProps({
  card: {
    type: Object,
    required: true,
  },
  showChallenge: {
    type: Boolean,
    default: false,
  },
});

const crownImageUrl = "/static/icons/challenge-crown-transparent.png";

const completedRoundCount = computed(() => Number(props.card.challenge?.completed_rounds || 0));
</script>

<template>
  <div class="word-card-body">
    <div class="word-card-title">
      <strong>{{ card.list.name }}</strong>
      <span v-if="showChallenge && card.challenge" class="challenge-round-inline" title="挑战次数">
        <img class="challenge-round-crown" :src="crownImageUrl" alt="" aria-hidden="true">
        <strong>X{{ completedRoundCount }}</strong>
      </span>
      <span v-if="card.challenge" class="challenge-summary-badge">
        已挑战{{ card.challenge.completed }}/{{ card.challenge.total }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.word-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.word-card-title > strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.challenge-round-inline {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #111827;
  font-size: 18px;
  font-weight: 900;
  line-height: 1;
  white-space: nowrap;
}

.challenge-round-crown {
  width: 34px;
  height: 34px;
  display: block;
  object-fit: contain;
  filter: drop-shadow(0 2px 3px rgba(120, 53, 15, 0.22));
}

.challenge-summary-badge {
  margin-left: auto;
}
</style>
