<script setup>
import ListDetailPage from "../pages/ListDetailPage.vue";
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
    v-if="ctx.route.name === 'lists' && ctx.data"
    :data="ctx.data"
    :upload-options="ctx.uploadOptions"
    :upload-form="ctx.uploadForm"
    :batch-image-state="ctx.batchImageState"
    :submit-upload="ctx.submitUpload"
    :submit-batch-images="ctx.submitBatchImages"
    :fallback-letter="ctx.fallbackLetter"
    :go="ctx.go"
  />
  <ListDetailPage
    v-else-if="ctx.route.name === 'listDetail' && ctx.data"
    :data="ctx.data"
    :delete-list-state="ctx.deleteListState"
    :rename-list="ctx.renameList"
    :delete-list="ctx.deleteList"
    :sync-list-images="ctx.syncListImages"
    :word-detail-url="ctx.wordDetailUrl"
    :image-for-word="ctx.imageForWord"
    :fallback-letter="ctx.fallbackLetter"
    :go="ctx.go"
  />
</template>
