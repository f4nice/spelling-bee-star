<script setup>
import { computed } from "vue";
import ImportPreviewTableHead from "./ImportPreviewTableHead.vue";
import ImportPreviewTableRow from "./ImportPreviewTableRow.vue";

const props = defineProps({
  preview: {
    type: Object,
    required: true,
  },
  importForm: {
    type: Object,
    required: true,
  },
});

const visibleRows = computed(() => (props.preview.rows || []).slice(0, 300));
const hiddenRowCount = computed(() => Math.max((props.preview.rows || []).length - visibleRows.value.length, 0));
</script>

<template>
  <p v-if="hiddenRowCount" class="preview-table-note">
    已选择全部 {{ preview.rows.length }} 行，当前仅展示前 {{ visibleRows.length }} 行用于预览。
  </p>
  <div class="table-wrap">
    <table class="preview-table">
      <ImportPreviewTableHead :columns="preview.columns" :import-form="importForm" />
      <tbody>
        <ImportPreviewTableRow
          v-for="row in visibleRows"
          :key="row.index"
          :row="row"
          :columns="preview.columns"
          :import-form="importForm"
        />
      </tbody>
    </table>
  </div>
</template>
