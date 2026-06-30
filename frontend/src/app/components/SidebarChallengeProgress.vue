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

function challengeLink(item) {
  const total = Math.max(Number(item.total || 0), 0);
  const completed = Math.min(Math.max(Number(item.completed || 0), 0), total);
  const remaining = Math.max(total - completed, 0);
  const maxChallengeCount = Math.min(Math.max(total, 1), 500);
  const dailyCount = remaining > 0 ? Math.min(remaining, maxChallengeCount) : maxChallengeCount;
  const startCount = remaining > 0 ? completed : 0;
  const params = new URLSearchParams({
    daily_count: String(dailyCount),
    start_count: String(startCount),
  });
  if (remaining <= 0 && total > 0) params.set("restart", "1");
  return `/challenge/${item.id}?${params.toString()}`;
}
</script>

<template>
  <div class="challenge-sidebar">
    <div class="challenge-sidebar-title">挑战进度</div>
    <a
      v-for="item in challenges"
      :key="item.id"
      class="challenge-progress-link"
      :href="challengeLink(item)"
      @click.prevent="navigate(challengeLink(item))"
    >
      <strong>{{ item.name }}</strong>
      <span>{{ item.completed }} / {{ item.total }}</span>
      <div class="sidebar-progress"><i :style="{ width: `${item.percent}%` }"></i></div>
    </a>
    <p v-if="!challenges.length">还没有可挑战的单词表。</p>
  </div>
</template>
