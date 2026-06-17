<script setup>
defineProps({
  wordList: {
    type: Object,
    required: true,
  },
  wordCount: {
    type: Number,
    required: true,
  },
});
</script>

<template>
  <div>
    <input v-model="wordList.name" class="list-title-input">
    <p>{{ wordCount }} 个单词</p>
  </div>
</template>
