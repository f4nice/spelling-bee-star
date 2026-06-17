<script setup>
defineProps({
  today: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div class="challenge-large-progress">
    <span :style="{ width: `${today.percent}%` }"></span>
  </div>

  <div class="challenge-stats">
    <div><span>本组一共</span><strong>{{ today.total }}</strong><span>个</span></div>
    <div><span>已答</span><strong>{{ today.answered }}</strong><span>个</span></div>
    <div><span>剩余</span><strong>{{ today.remaining }}</strong><span>个</span></div>
    <div><span>本次正确</span><strong class="result-correct">{{ today.correct }}</strong><span>个</span></div>
    <div><span>本次错误</span><strong class="result-wrong">{{ today.wrong }}</strong><span>个</span></div>
  </div>
</template>
