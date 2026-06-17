<script setup>
import ImportPreviewTableHead from "./ImportPreviewTableHead.vue";
import ImportPreviewTableRow from "./ImportPreviewTableRow.vue";

defineProps({
  preview: {
    type: Object,
    required: true,
  },
  importForm: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div class="table-wrap">
    <table class="preview-table">
      <ImportPreviewTableHead :columns="preview.columns" :import-form="importForm" />
      <tbody>
        <ImportPreviewTableRow
          v-for="row in preview.rows"
          :key="row.index"
          :row="row"
          :columns="preview.columns"
          :import-form="importForm"
        />
      </tbody>
    </table>
  </div>
</template>
