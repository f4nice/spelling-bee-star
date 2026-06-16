<script setup>
defineProps({
  sourceUrl: {
    type: String,
    required: true,
  },
});
</script>

<template>
  <section class="panel newspaper-hero">
    <div>
      <p class="newspaper-kicker">China Daily Reader</p>
      <h1>英文小报</h1>
      <p>精选 China Daily 英文资讯，适合日常泛读和积累新闻表达。</p>
    </div>
    <a class="ghost-button" :href="sourceUrl" target="_blank" rel="noreferrer">China Daily</a>
  </section>
</template>
