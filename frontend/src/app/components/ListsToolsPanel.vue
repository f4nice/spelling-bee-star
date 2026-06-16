<script setup>
import BatchImageToolCard from "./BatchImageToolCard.vue";
import ListImportToolCard from "./ListImportToolCard.vue";

defineProps({
  data: {
    type: Object,
    required: true,
  },
  uploadOptions: {
    type: Object,
    required: true,
  },
  uploadForm: {
    type: Object,
    required: true,
  },
  submitUpload: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <section class="panel lists-tools-panel">
    <ListImportToolCard
      :upload-options="uploadOptions"
      :upload-form="uploadForm"
      :submit-upload="submitUpload"
    />
    <BatchImageToolCard :cards="data.cards" />
  </section>
</template>
