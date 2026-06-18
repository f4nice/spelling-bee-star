<script setup>
import ListsPage from "../pages/ListsPage.vue";

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <ListsPage
    v-if="ctx.data"
    :data="ctx.data"
    :upload-options="ctx.uploadOptions"
    :upload-form="ctx.uploadForm"
    :batch-image-state="ctx.batchImageState"
    :submit-upload="ctx.submitUpload"
    :submit-batch-images="ctx.submitBatchImages"
    :fallback-letter="ctx.fallbackLetter"
    :go="ctx.go"
  />
</template>
