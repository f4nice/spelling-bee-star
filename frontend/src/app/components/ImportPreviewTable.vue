<script setup>
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
      <thead>
        <tr>
          <th>导入</th>
          <th>Excel 行</th>
          <th v-for="column in preview.columns" :key="column">
            <label class="check-label">
              <input v-model="importForm.selected_columns" type="checkbox" :value="column">
              <span>{{ column }}</span>
            </label>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in preview.rows" :key="row.index">
          <td><input v-model="importForm.selected_rows" type="checkbox" :value="row.index"></td>
          <td>{{ row.excel_row }}</td>
          <td v-for="column in preview.columns" :key="column">{{ row.values[column] || '' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
