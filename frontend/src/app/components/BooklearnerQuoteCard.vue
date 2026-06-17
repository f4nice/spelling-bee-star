<script setup>
defineProps({
  item: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <article class="quote-card">
    <p>{{ item.quote || item.text || item.sentence }}</p>
    <strong>{{ item.title || item.bookTitle || item.book }}</strong>
  </article>
</template>
