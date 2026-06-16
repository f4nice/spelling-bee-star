<script setup>
defineProps({
  syncJob: {
    type: Object,
    default: null,
  },
  syncListImages: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <section class="panel image-sync-panel">
    <div class="sync-summary">
      <div class="sync-heading">
        <strong>图片同步</strong>
        <span v-if="syncJob">{{ syncJob.done }} / {{ syncJob.total }}</span>
      </div>
      <p>{{ syncJob?.message || '查找缺失图片，下载并压缩到服务器图片库。' }}</p>
    </div>
    <button class="secondary-button sync-image-button" type="button" @click="syncListImages">同步图片</button>
  </section>
</template>
