<script setup>
defineProps({
  syncJob: {
    type: Object,
    default: null,
  },
});
</script>

<template>
  <div class="sync-summary">
    <div class="sync-heading">
      <strong>图片同步</strong>
      <span v-if="syncJob">{{ syncJob.done }} / {{ syncJob.total }}</span>
    </div>
    <p>{{ syncJob?.message || '查找缺失图片，下载并压缩到服务器图片库。' }}</p>
  </div>
</template>
