<script setup>
defineProps({
  state: {
    type: Object,
    required: true,
  },
  restartUrl: {
    type: String,
    required: true,
  },
});
</script>

<template>
  <div class="challenge-complete">
    <h2>{{ state.today_challenge.all_complete ? "太棒了，整组都拿下了" : "今日目标完成了" }}</h2>
    <div class="challenge-result-grid">
      <div><span>本次挑战</span><strong>{{ state.today_challenge.answered }} / {{ state.today_challenge.total }}</strong></div>
      <div><span>答对</span><strong class="result-correct">{{ state.today_challenge.correct }}</strong></div>
      <div><span>答错</span><strong class="result-wrong">{{ state.today_challenge.wrong }}</strong></div>
      <div><span>正确率</span><strong>{{ state.today_challenge.accuracy }}%</strong></div>
    </div>
    <div class="challenge-complete-actions">
      <a class="secondary-button" :href="restartUrl">再练一组</a>
    </div>
  </div>
</template>
