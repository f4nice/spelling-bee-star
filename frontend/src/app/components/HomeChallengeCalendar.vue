<script setup>
import HomeChallengeCalendarDay from "./HomeChallengeCalendarDay.vue";
import HomeChallengeCalendarHeading from "./HomeChallengeCalendarHeading.vue";

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
    <HomeChallengeCalendarHeading :calendar="calendar" />
    <div class="challenge-calendar">
      <div v-for="weekday in calendar.weekdays" :key="weekday" class="calendar-weekday">{{ weekday }}</div>
      <template v-for="(week, weekIndex) in calendar.weeks" :key="weekIndex">
        <HomeChallengeCalendarDay
          v-for="(day, dayIndex) in week"
          :key="`${weekIndex}-${dayIndex}`"
          :day="day"
          @open-day="go(`/challenge-calendar/${$event}`)"
        />
      </template>
    </div>
  </section>
</template>
