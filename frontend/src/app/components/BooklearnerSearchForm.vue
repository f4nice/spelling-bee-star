<script setup>
defineProps({
  book: {
    type: Object,
    required: true,
  },
  analyzeBookQuery: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <label>书名或作者</label>
  <div class="input-row">
    <input v-model="book.query" placeholder="Pride and Prejudice">
    <button type="button" @click="analyzeBookQuery">分析</button>
  </div>
</template>
