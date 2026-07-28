<script setup>
import ImportPreviewSelectionActions from "./ImportPreviewSelectionActions.vue";
import ImportPreviewSheetControls from "./ImportPreviewSheetControls.vue";
import ImportPreviewSubmitButton from "./ImportPreviewSubmitButton.vue";
import { importPreviewToolbarProps } from "../props/importPreviewToolbarProps.js";

defineProps(importPreviewToolbarProps);
</script>

<template>
  <div class="import-toolbar" role="group" aria-label="导入预览工具栏">
    <ImportPreviewSheetControls
      :preview="preview"
      :import-form="importForm"
      :change-preview-sheet="changePreviewSheet"
    />
    <ImportPreviewSelectionActions :set-all-rows="setAllRows" :set-all-columns="setAllColumns" />
    <ImportPreviewSubmitButton
      :submit-import="submitImport"
      :import-job="importJob"
      :is-importing="isImporting"
    />
  </div>
</template>
