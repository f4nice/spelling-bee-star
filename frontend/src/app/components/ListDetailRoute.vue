<script setup>
import ListDetailPage from "../pages/ListDetailPage.vue";

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <ListDetailPage
    v-if="ctx.data"
    :data="ctx.data"
    :upload-options="ctx.uploadOptions"
    :upload-form="ctx.uploadForm"
    :delete-list-state="ctx.deleteListState"
    :ai-image-job="ctx.aiImageJob"
    :submit-upload="ctx.submitUpload"
    :rename-list="ctx.renameList"
    :delete-list="ctx.deleteList"
    :move-list-to-group="ctx.moveListToGroup"
    :generate-list-ai-images="ctx.generateListAiImages"
    :word-detail-url="ctx.wordDetailUrl"
    :image-for-word="ctx.imageForWord"
    :fallback-letter="ctx.fallbackLetter"
    :go="ctx.go"
  />
</template>
