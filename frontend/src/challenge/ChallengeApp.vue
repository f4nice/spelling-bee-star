<script setup>
import ChallengeComplete from "./ChallengeComplete.vue";
import ChallengeHeader from "./ChallengeHeader.vue";
import ChallengeStats from "./ChallengeStats.vue";
import ChallengeWordCard from "./ChallengeWordCard.vue";
import { restartChallengeUrl } from "./challengeRouteState.js";
import { useChallengeSession } from "./useChallengeSession.js";

const props = defineProps({
  wordListId: {
    type: Number,
    default: null,
  },
});

const wordListId = Number(props.wordListId || 0);
const { state, spelling, loading, submitting, errorMessage, submitSpelling } = useChallengeSession(wordListId);
</script>

<template>
  <section class="panel challenge-panel spelling-challenge-panel">
    <div v-if="loading" class="empty-state">正在加载挑战...</div>
    <div v-else-if="errorMessage" class="error-box">{{ errorMessage }}</div>
    <template v-else-if="state">
      <ChallengeHeader :state="state" :word-list-id="wordListId" />
      <ChallengeStats :today="state.today_challenge" />

      <ChallengeWordCard
        v-if="state.current_word"
        v-model:spelling="spelling"
        :state="state"
        :submitting="submitting"
        @submit="submitSpelling"
      />
      <ChallengeComplete v-else :state="state" :restart-url="restartChallengeUrl(wordListId)" />
    </template>
  </section>
</template>
