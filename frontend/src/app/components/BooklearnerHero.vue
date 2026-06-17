<script setup>
import BooklearnerFeaturedQuotes from "./BooklearnerFeaturedQuotes.vue";
import BooklearnerHeroActions from "./BooklearnerHeroActions.vue";
import { booklearnerHeroProps } from "../props/booklearnerHeroProps.js";

defineProps(booklearnerHeroProps);
</script>

<template>
  <section class="quote-home-panel">
    <div class="quote-home-head">
      <div>
        <h1>好词好句</h1>
        <p>从书籍学习记录里整理短句、难词和阅读关注点。</p>
      </div>
      <BooklearnerHeroActions :go="go" />
    </div>

    <BooklearnerFeaturedQuotes :route="route" :book="book" />
  </section>
</template>
