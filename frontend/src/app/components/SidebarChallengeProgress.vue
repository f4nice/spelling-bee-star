<script setup>
defineProps({
  challenges: {
    type: Array,
    required: true,
  },
  navigate: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="challenge-sidebar">
    <div class="challenge-sidebar-title">挑战进度</div>
    <a
      v-for="item in challenges"
      :key="item.id"
      class="challenge-progress-link"
      :href="`/challenge/${item.id}`"
      @click.prevent="navigate(`/challenge/${item.id}`)"
    >
      <strong>{{ item.name }}</strong>
      <span>{{ item.completed }} / {{ item.total }}</span>
      <div class="sidebar-progress"><i :style="{ width: `${item.percent}%` }"></i></div>
    </a>
    <p v-if="!challenges.length">还没有可挑战的单词表。</p>
  </div>
</template>
