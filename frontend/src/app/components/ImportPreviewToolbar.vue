<script setup>
import ImportPreviewImagePicker from "./ImportPreviewImagePicker.vue";
import ImportPreviewSelectionActions from "./ImportPreviewSelectionActions.vue";
import ImportPreviewSheetControls from "./ImportPreviewSheetControls.vue";

defineProps({
  preview: {
    type: Object,
    required: true,
  },
  importForm: {
    type: Object,
    required: true,
  },
  changePreviewSheet: {
    type: Function,
    required: true,
  },
  setAllRows: {
    type: Function,
    required: true,
  },
  setAllColumns: {
    type: Function,
    required: true,
  },
  submitImport: {
    type: Function,
    required: true,
  },
});
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
    <button type="button" @click="submitImport">确认导入</button>
  </div>
</template>
