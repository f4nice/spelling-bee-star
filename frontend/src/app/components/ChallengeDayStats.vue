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
  activeFilter: {
    type: String,
    default: "all",
  },
  wrongChallengeUrl: {
    type: String,
    default: "",
  },
  go: {
    type: Function,
    required: true,
  },
});

defineEmits(["filter"]);
</script>

<template>
  <section class="challenge-day-stats">
    <div class="panel challenge-day-filter" :class="{ active: activeFilter === 'correct' }">
      <span>答对</span>
      <button class="challenge-day-stat-number stat-correct" type="button" @click="$emit('filter', 'correct')">
        {{ correct }}
      </button>
    </div>
    <div class="panel challenge-day-filter" :class="{ active: activeFilter === 'wrong' }">
      <span>答错</span>
      <div class="challenge-day-wrong-actions">
        <button class="challenge-day-stat-number stat-wrong" type="button" @click="$emit('filter', 'wrong')">
          {{ wrong }}
        </button>
        <button
          class="secondary-button challenge-day-start-button"
          type="button"
          :disabled="!wrongChallengeUrl || wrong <= 0"
          @click="go(wrongChallengeUrl)"
        >
          发起挑战
        </button>
      </div>
    </div>
    <button class="panel challenge-day-back" type="button" @click="go('/')">
      <span>返回</span>
      <strong>挑战日历</strong>
    </button>
  </section>
</template>
