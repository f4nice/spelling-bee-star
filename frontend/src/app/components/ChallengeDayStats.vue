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
  wrongAttempts: {
    type: Number,
    default: 0,
  },
  corrected: {
    type: Number,
    default: 0,
  },
  correctionPending: {
    type: Number,
    default: 0,
  },
  activeFilter: {
    type: String,
    default: "all",
  },
  wrongChallengeUrl: {
    type: String,
    default: "",
  },
  wrongChallengeCount: {
    type: Number,
    default: 0,
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
      <div class="challenge-day-stat-heading">
        <span>答错</span>
        <span class="challenge-day-correction-count">纠正 {{ corrected }}</span>
      </div>
      <button class="challenge-day-stat-number stat-wrong" type="button" @click="$emit('filter', 'wrong')">
        {{ wrong }}
      </button>
      <small v-if="wrongAttempts && wrongAttempts !== wrong">错误次数 {{ wrongAttempts }}</small>
      <small v-else>错词数量</small>
    </div>
    <div class="panel challenge-day-filter" :class="{ active: activeFilter === 'pending' }">
      <span>待纠正</span>
      <div class="challenge-day-wrong-actions">
        <button class="challenge-day-stat-number stat-pending" type="button" @click="$emit('filter', 'pending')">
          {{ correctionPending }}
        </button>
        <button
          class="secondary-button challenge-day-start-button"
          type="button"
          :disabled="!wrongChallengeUrl || wrongChallengeCount <= 0"
          @click="go(wrongChallengeUrl)"
        >
          发起挑战
        </button>
      </div>
      <small>{{ correctionPending > 0 ? '还没练对' : '已清空' }}</small>
    </div>
    <button class="panel challenge-day-back" type="button" @click="go('/')">
      <span>返回</span>
      <strong>挑战日历</strong>
    </button>
  </section>
</template>
