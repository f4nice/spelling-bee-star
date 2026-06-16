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
  <div class="word-column-options">
    <label v-for="column in columns" :key="column" class="word-column-option">
      <input v-model="importForm.word_columns" type="checkbox" :value="column">
      <span>{{ column }}</span>
    </label>
  </div>
</template>
