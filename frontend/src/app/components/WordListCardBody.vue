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
      <span v-if="card.challenge" class="challenge-summary-badge">
        已挑战 {{ card.challenge.completed }} 个，共 {{ card.challenge.total }} 个
      </span>
    </div>
  </div>
</template>
