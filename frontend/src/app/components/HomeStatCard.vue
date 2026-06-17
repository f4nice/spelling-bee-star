<script setup>
defineProps({
  card: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <button class="home-stat-card panel" type="button" @click="go(card.path)">
    <span>{{ card.label }}</span>
    <strong>{{ card.value }}</strong>
    <small>{{ card.detail }}</small>
  </button>
</template>
