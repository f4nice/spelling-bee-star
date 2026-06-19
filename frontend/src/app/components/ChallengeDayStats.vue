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
  go: {
    type: Function,
    required: true,
  },
});

defineEmits(["filter"]);
</script>

<template>
  <section class="challenge-day-stats">
    <button
      class="panel challenge-day-filter"
      :class="{ active: activeFilter === 'correct' }"
      type="button"
      @click="$emit('filter', 'correct')"
    >
      <span>答对</span>
      <strong class="stat-correct">{{ correct }}</strong>
    </button>
    <button
      class="panel challenge-day-filter"
      :class="{ active: activeFilter === 'wrong' }"
      type="button"
      @click="$emit('filter', 'wrong')"
    >
      <span>答错</span>
      <strong class="stat-wrong">{{ wrong }}</strong>
    </button>
    <button class="panel challenge-day-back" type="button" @click="go('/')">
      <span>返回</span>
      <strong>挑战日历</strong>
    </button>
  </section>
</template>
