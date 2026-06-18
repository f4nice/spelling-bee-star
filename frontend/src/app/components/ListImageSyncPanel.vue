<script setup>
import ListImageSyncSummary from "./ListImageSyncSummary.vue";

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
    <ListImageSyncSummary :sync-job="syncJob" />
    <button class="secondary-button sync-image-button" type="button" @click="syncListImages">同步图片</button>
  </section>
</template>
