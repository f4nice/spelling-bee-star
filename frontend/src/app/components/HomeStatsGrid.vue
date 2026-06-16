<script setup>
defineProps({
  stats: {
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
  <section class="home-stats-grid">
    <button class="home-stat-card panel" type="button" @click="go('/lists')">
      <span>我的单词表</span>
      <strong>{{ stats.word_lists }}</strong>
      <small>{{ stats.words }} 个单词</small>
    </button>
    <button class="home-stat-card panel" type="button" @click="go('/newspaper')">
      <span>英文小报</span>
      <strong>Today</strong>
      <small>China Daily 今日泛读</small>
    </button>
    <button class="home-stat-card panel" type="button" @click="go('/booklearner')">
      <span>好词好句</span>
      <strong>Books</strong>
      <small>书摘与难点词</small>
    </button>
    <button class="home-stat-card panel" type="button" @click="go('/wrong-words')">
      <span>我的生词本</span>
      <strong>{{ stats.wrong_words }}</strong>
      <small>今日 {{ stats.today_wrong_count }} 个</small>
    </button>
  </section>
</template>
