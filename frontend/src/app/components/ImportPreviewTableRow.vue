<script setup>
defineProps({
  row: {
    type: Object,
    required: true,
  },
  columns: {
    type: Array,
    required: true,
  },
  importForm: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <tr>
    <td><input v-model="importForm.selected_rows" type="checkbox" :value="row.index"></td>
    <td>{{ row.excel_row }}</td>
    <td v-for="column in columns" :key="column">{{ row.values[column] || "" }}</td>
  </tr>
</template>
