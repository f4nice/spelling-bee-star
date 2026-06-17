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
      <h1>{{ state.word_list.name }}</h1>
      <p>
        总进度 {{ state.challenge.completed }} / {{ state.challenge.total }}
        · 今日目标 {{ state.today_challenge.done }} / {{ state.today_challenge.total }}
      </p>
    </div>
    <a class="ghost-button" :href="`/lists/${wordListId}`">返回单词表</a>
  </div>
</template>
