<script setup>
defineProps({
  correct: {
    type: Number,
    required: true,
  },
  wrong: {
    type: Number,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <section class="challenge-day-stats">
    <div class="panel challenge-day-filter">
      <span>答对</span>
      <strong class="stat-correct">{{ correct }}</strong>
    </div>
    <div class="panel challenge-day-filter">
      <span>答错</span>
      <strong class="stat-wrong">{{ wrong }}</strong>
    </div>
    <button class="panel challenge-day-back" type="button" @click="go('/')">
      <span>返回</span>
      <strong>挑战日历</strong>
    </button>
  </section>
</template>
