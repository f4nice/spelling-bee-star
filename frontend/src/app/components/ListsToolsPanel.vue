<script setup>
import BatchImageToolCard from "./BatchImageToolCard.vue";
import ListImportToolCard from "./ListImportToolCard.vue";
import { listsToolsPanelProps } from "../props/listsToolsPanelProps.js";

defineProps(listsToolsPanelProps);
</script>

<template>
  <section class="panel lists-tools-panel">
    <ListImportToolCard
      :upload-options="uploadOptions"
      :upload-form="uploadForm"
      :submit-upload="submitUpload"
    />
    <BatchImageToolCard
      :cards="data.cards"
      :batch-image-state="batchImageState"
      :submit-batch-images="submitBatchImages"
    />
  </section>
</template>
