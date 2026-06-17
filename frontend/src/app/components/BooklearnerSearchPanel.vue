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
  <div class="form active" role="group" aria-label="按书名分析">
    <label>书名或作者</label>
    <div class="input-row">
      <input v-model="book.query" placeholder="Pride and Prejudice">
      <button type="button" @click="analyzeBookQuery">分析</button>
    </div>
  </div>
</template>
