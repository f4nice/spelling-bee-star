<script setup>
import BooklearnerHistoryCard from "./BooklearnerHistoryCard.vue";

defineProps({
  book: {
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
  <section class="word-grid">
    <BooklearnerHistoryCard
      v-for="item in book.history"
      :key="item.id"
      :item="item"
      :go="go"
    />
  </section>
</template>
