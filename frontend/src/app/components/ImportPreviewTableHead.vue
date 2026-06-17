<script setup>
defineProps({
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
  <thead>
    <tr>
      <th>导入</th>
      <th>Excel 行</th>
      <th v-for="column in columns" :key="column">
        <label class="check-label">
          <input v-model="importForm.selected_columns" type="checkbox" :value="column">
          <span>{{ column }}</span>
        </label>
      </th>
    </tr>
  </thead>
</template>
