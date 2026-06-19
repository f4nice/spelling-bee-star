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
    :submit-upload="ctx.submitUpload"
    :rename-list="ctx.renameList"
    :delete-list="ctx.deleteList"
    :sync-list-images="ctx.syncListImages"
    :word-detail-url="ctx.wordDetailUrl"
    :image-for-word="ctx.imageForWord"
    :fallback-letter="ctx.fallbackLetter"
    :go="ctx.go"
  />
</template>
