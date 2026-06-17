<script setup>
defineProps({
  calendar: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <section class="panel calendar-panel home-calendar">
    <div class="calendar-heading">
      <div>
        <p class="section-kicker">Challenge</p>
        <h2>挑战日历</h2>
        <p>
          {{ calendar.title }} · 本月答对 {{ calendar.month_correct }} 个，答错
          {{ calendar.month_wrong }} 个
        </p>
      </div>
    </div>
    <div class="challenge-calendar">
      <div v-for="weekday in calendar.weekdays" :key="weekday" class="calendar-weekday">{{ weekday }}</div>
      <template v-for="(week, weekIndex) in calendar.weeks" :key="weekIndex">
        <button
          v-for="(day, dayIndex) in week"
          :key="`${weekIndex}-${dayIndex}`"
          type="button"
          class="calendar-day"
          style="display: flex; flex-direction: column; align-items: flex-start;"
          :class="{ today: day.is_today, empty: !day.day, 'has-records': day.total }"
          :disabled="!day.total"
          @click="day.total && go(`/challenge-calendar/${day.date}`)"
        >
          <span v-if="day.day" class="calendar-day-number">{{ day.day }}</span>
          <span v-if="day.total" class="calendar-total" style="display: inline-flex; align-items: baseline; gap: 2px;">
            <strong>{{ day.total }}</strong>
            <span>个</span>
          </span>
        </button>
      </template>
    </div>
  </section>
</template>
