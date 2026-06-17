<script setup>
import BooklearnerQuoteCard from "./BooklearnerQuoteCard.vue";

defineProps({
  route: {
    type: Object,
    required: true,
  },
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
  <section class="quote-home-panel">
    <div class="quote-home-head">
      <div>
        <h1>好词好句</h1>
        <p>从书籍学习记录里整理短句、难词和阅读关注点。</p>
      </div>
      <div class="quote-head-actions">
        <button class="quote-more-link" type="button" @click="go('/booklearner')">首页</button>
        <button class="quote-more-link" type="button" @click="go('/booklearner/quotes')">更多</button>
        <button class="quote-more-link quote-upload-link" type="button" @click="go('/booklearner/upload')">上传</button>
      </div>
    </div>

    <div class="featured-quotes" :class="{ 'featured-quotes-list': route.name === 'booklearnerQuotes' }">
      <BooklearnerQuoteCard
        v-for="item in book.featured"
        :key="item.id || item.quote"
        :item="item"
      />
      <div v-if="!book.featured.length" class="quote-feed-empty">还没有书摘。</div>
    </div>
  </section>
</template>
