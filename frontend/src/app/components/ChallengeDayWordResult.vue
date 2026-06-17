<script setup>
defineProps({
  item: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <span class="challenge-day-result">{{ item.status === 'correct' ? '✓' : '×' }}</span>
  <strong class="challenge-day-status" :class="item.status === 'correct' ? 'is-correct' : 'is-wrong'">
    {{ item.status === 'correct' ? '正确' : '错误' }}
  </strong>
</template>
