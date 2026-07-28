<script setup>
import ImportPreviewHeader from "../components/ImportPreviewHeader.vue";
import ImportPreviewProgress from "../components/ImportPreviewProgress.vue";
import ImportPreviewTable from "../components/ImportPreviewTable.vue";
import ImportPreviewToolbar from "../components/ImportPreviewToolbar.vue";
import ImportWordColumnOptions from "../components/ImportWordColumnOptions.vue";

defineProps([
  "data",
  "importForm",
  "go",
  "changePreviewSheet",
  "setAllRows",
  "setAllColumns",
  "submitImport",
  "importJob",
  "isImporting"
]);
</script>

<template>
  <section class="panel preview-panel">
    <ImportPreviewHeader :preview="data.preview" :go="go" />
    <ImportPreviewToolbar
      :preview="data.preview"
      :import-form="importForm"
      :change-preview-sheet="changePreviewSheet"
      :set-all-rows="setAllRows"
      :set-all-columns="setAllColumns"
      :submit-import="submitImport"
      :import-job="importJob"
      :is-importing="isImporting"
    />
    <ImportPreviewProgress v-if="importJob" :job="importJob" />
    <ImportWordColumnOptions :columns="data.preview.columns" :import-form="importForm" />
    <ImportPreviewTable :preview="data.preview" :import-form="importForm" />
  </section>
</template>
