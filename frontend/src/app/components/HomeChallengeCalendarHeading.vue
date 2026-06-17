<script setup>
defineProps({
  calendar: {
    type: Object,
    required: true,
  },
});
</script>

<template>
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
</template>
