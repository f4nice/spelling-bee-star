<script setup>
defineProps({
  data: {
    type: Object,
    required: true,
  },
  wordNavUrl: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="detail-study-row">
    <div class="auto-study-controls">
      <a class="secondary-button" :href="wordNavUrl(data.navigation.previous_word_id)">上一个</a>
      <a class="secondary-button" :href="wordNavUrl(data.navigation.next_word_id)">下一个</a>
    </div>
  </div>
</template>
