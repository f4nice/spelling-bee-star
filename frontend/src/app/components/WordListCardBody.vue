<script setup>
defineProps({
  card: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div class="word-card-body">
    <div class="word-card-title">
      <strong>{{ card.list.name }}</strong>
      <span class="status">{{ card.count }} 词</span>
    </div>
  </div>
</template>
