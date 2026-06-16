<script setup>
import PreviewPage from '../pages/PreviewPage.vue';
import UploadPage from '../pages/UploadPage.vue';

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <UploadPage
    v-if="ctx.route.name === 'upload'"
    :upload-form="ctx.uploadForm"
    :upload-options="ctx.uploadOptions"
    :submit-upload="ctx.submitUpload"
  />
  <PreviewPage
    v-else
    :data="ctx.data"
    :import-form="ctx.importForm"
    :go="ctx.go"
    :change-preview-sheet="ctx.changePreviewSheet"
    :set-all-rows="ctx.setAllRows"
    :set-all-columns="ctx.setAllColumns"
    :submit-import="ctx.submitImport"
  />
</template>
