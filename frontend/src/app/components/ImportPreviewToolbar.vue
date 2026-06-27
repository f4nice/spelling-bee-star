<script setup>
import ImportPreviewImagePicker from "./ImportPreviewImagePicker.vue";
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
    <ImportPreviewImagePicker :import-form="importForm" />
    <ImportPreviewSubmitButton :submit-import="submitImport" :is-importing="isImporting" />
  </div>
</template>
