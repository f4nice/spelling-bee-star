<script setup>
import BooklearnerQuoteCard from "./BooklearnerQuoteCard.vue";
import { booklearnerFeaturedQuotesProps } from "../props/booklearnerFeaturedQuotesProps.js";

defineProps(booklearnerFeaturedQuotesProps);
</script>

<template>
  <div class="featured-quotes" :class="{ 'featured-quotes-list': route.name === 'booklearnerQuotes' }">
    <BooklearnerQuoteCard
      v-for="item in book.featured"
      :key="item.id || item.quote"
      :item="item"
    />
    <div v-if="!book.featured.length" class="quote-feed-empty">还没有书摘。</div>
  </div>
</template>
