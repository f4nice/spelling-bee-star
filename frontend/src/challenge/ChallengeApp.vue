<script setup>
import ChallengeComplete from './ChallengeComplete.vue';
import ChallengeWordCard from './ChallengeWordCard.vue';
import { useChallengeSession } from './useChallengeSession.js';

const props = defineProps({
  wordListId: {
    type: Number,
    default: null,
  },
});

const root = document.getElementById('challenge-vue-app');
const wordListId = Number(props.wordListId || root?.dataset.wordListId || 0);
const {
  state,
  spelling,
  loading,
  submitting,
  errorMessage,
  submitSpelling,
  stripDigits,
} = useChallengeSession(wordListId);

function legacyChallengeUrl(extra = '') {
  return `/challenge/${wordListId}${extra}`;
}
</script>

<template>
  <section class="panel challenge-panel vue-challenge-panel">
    <div v-if="loading" class="empty-state">正在加载挑战...</div>
    <div v-else-if="errorMessage" class="error-box">{{ errorMessage }}</div>
    <template v-else-if="state">
      <div class="challenge-top">
        <div>
          <p class="section-kicker">Vue Challenge</p>
          <h1>{{ state.word_list.name }}</h1>
          <p>
            总进度 {{ state.challenge.completed }} / {{ state.challenge.total }}
            · 今日目标 {{ state.today_challenge.done }} / {{ state.today_challenge.total }}
          </p>
        </div>
        <a class="ghost-button" :href="`/lists/${wordListId}`">返回单词表</a>
      </div>

      <div class="challenge-large-progress">
        <span :style="{ width: `${state.today_challenge.percent}%` }"></span>
      </div>

      <div class="challenge-stats">
        <div><span>本组一共</span><strong>{{ state.today_challenge.total }}</strong><span>个</span></div>
        <div><span>已答</span><strong>{{ state.today_challenge.answered }}</strong><span>个</span></div>
        <div><span>剩余</span><strong>{{ state.today_challenge.remaining }}</strong><span>个</span></div>
        <div><span>本次正确</span><strong class="result-correct">{{ state.today_challenge.correct }}</strong><span>个</span></div>
        <div><span>本次错误</span><strong class="result-wrong">{{ state.today_challenge.wrong }}</strong><span>个</span></div>
      </div>

      <ChallengeWordCard
        v-if="state.current_word"
        v-model:spelling="spelling"
        :state="state"
        :submitting="submitting"
        @submit="submitSpelling"
        @strip-digits="stripDigits"
      />
      <ChallengeComplete v-else :state="state" :legacy-url="legacyChallengeUrl(`?daily_count=20&start_count=0`)" />
    </template>
  </section>
</template>
