<script setup>
defineProps({
  day: {
    type: Object,
    required: true,
  },
});

defineEmits(["open-day"]);
</script>

<template>
  <button
    type="button"
    class="calendar-day"
    :class="{ today: day.is_today, empty: !day.day, 'has-records': day.total }"
    :disabled="!day.total"
    @click="day.total && $emit('open-day', day.date)"
  >
    <span v-if="day.day" class="calendar-day-number">{{ day.day }}</span>
    <span v-if="day.total" class="calendar-total">
      <strong>{{ day.total }}</strong>
      <span>个</span>
    </span>
  </button>
</template>
