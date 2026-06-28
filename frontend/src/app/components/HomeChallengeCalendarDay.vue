<script setup>
import { computed } from "vue";

const props = defineProps({
  day: {
    type: Object,
    required: true,
  },
});

defineEmits(["open-day"]);

const firstDefined = (...values) => values.find((value) => value !== undefined && value !== null);

const toCount = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const totalCount = computed(() => toCount(props.day.total));
const wrongRaw = computed(() =>
  firstDefined(props.day.wrong, props.day.wrong_count, props.day.failed, props.day.failed_count),
);
const correctRaw = computed(() =>
  firstDefined(props.day.correct, props.day.correct_count, props.day.right, props.day.right_count),
);

const wrongCount = computed(() => toCount(wrongRaw.value));
const correctCount = computed(() => {
  if (correctRaw.value !== undefined) {
    return toCount(correctRaw.value);
  }
  return Math.max(totalCount.value - wrongCount.value, 0);
});
</script>

<template>
  <button
    type="button"
    class="calendar-day"
    :class="{ today: day.is_today, empty: !day.day, 'has-records': day.total }"
    :disabled="!day.total"
    @click="day.total && $emit('open-day', day.date)"
  >
    <span v-if="day.day" class="calendar-day-number">
      <span>{{ day.day }}</span>
    </span>
    <span v-if="day.total" class="calendar-result-lines" aria-label="挑战结果">
      <span class="calendar-result-line is-correct">
        <span>正确</span>
        <strong>{{ correctCount }}</strong>
      </span>
      <span class="calendar-result-line is-wrong">
        <span>错误</span>
        <strong>{{ wrongCount }}</strong>
      </span>
    </span>
  </button>
</template>
