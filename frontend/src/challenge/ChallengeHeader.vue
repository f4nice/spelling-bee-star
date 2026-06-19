<script setup>
defineProps({
  state: {
    type: Object,
    required: true,
  },
  wordListId: {
    type: Number,
    required: true,
  },
});
</script>

<template>
  <div class="challenge-top">
    <div>
      <p class="section-kicker">Spelling Challenge</p>
      <h1>拼写挑战</h1>
    </div>
    <div class="challenge-top-summary">
      <strong>{{ state.word_list.name }}</strong>
      <span>总进度 {{ state.challenge.completed }} / {{ state.challenge.total }}</span>
      <span>今日目标 {{ state.today_challenge.done }} / {{ state.today_challenge.total }}</span>
      <a class="ghost-button compact-button" :href="`/lists/${wordListId}`">返回单词表</a>
    </div>
  </div>
</template>
