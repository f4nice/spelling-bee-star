<script setup>
defineProps({
  sourceUrl: {
    type: String,
    required: true,
  },
  refreshing: Boolean,
  status: String,
});
defineEmits(["refresh"]);
</script>

<template>
  <section class="panel newspaper-hero">
    <div>
      <p class="newspaper-kicker">China Daily Reader</p>
      <h1>英文小报</h1>
      <p>精选 China Daily 英文资讯，适合日常泛读和积累新闻表达。</p>
      <p v-if="status" class="newspaper-cache-status" role="status">{{ status }}</p>
    </div>
    <div class="newspaper-hero-actions">
      <button type="button" class="primary-action-button" :disabled="refreshing" @click="$emit('refresh')">{{ refreshing ? "更新中…" : "更新小报" }}</button>
      <a class="ghost-button" :href="sourceUrl" target="_blank" rel="noreferrer">China Daily</a>
    </div>
  </section>
</template>

<style scoped>
.newspaper-hero-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.newspaper-hero .newspaper-cache-status { margin-top: 10px; font-size: 13px; color: #526b63; }
</style>
