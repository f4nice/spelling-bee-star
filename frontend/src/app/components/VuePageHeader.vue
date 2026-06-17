<script setup>
defineProps({
  routeTitle: {
    type: String,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <section class="panel vue-page-heading">
    <div>
      <p class="section-kicker">SpeakEasy</p>
      <h1>{{ routeTitle }}</h1>
    </div>
    <nav class="vue-page-nav" aria-label="页面导航">
      <button type="button" class="secondary-button" @click="go('/')">首页</button>
      <button type="button" class="secondary-button" @click="go('/lists')">我的单词表</button>
      <button type="button" class="secondary-button" @click="go('/upload')">导入</button>
      <button type="button" class="secondary-button" @click="go('/newspaper')">英文小报</button>
      <button type="button" class="secondary-button" @click="go('/booklearner')">好词好句</button>
      <button type="button" class="secondary-button" @click="go('/wrong-words')">我的生词本</button>
    </nav>
  </section>
</template>
