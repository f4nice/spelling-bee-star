<script setup>
import BooklearnerHeroActions from "./BooklearnerHeroActions.vue";
import { booklearnerHeroProps } from "../props/booklearnerHeroProps.js";

defineProps(booklearnerHeroProps);
</script>

<template>
  <section class="quote-home-panel booklearner-heading-panel">
    <div class="quote-home-head">
      <div>
        <h1>好词好句</h1>
        <p>按书籍整理英文摘录、阅读关注点和难点单词。</p>
      </div>
      <BooklearnerHeroActions :go="go" :open-upload-modal="openUploadModal" />
    </div>
  </section>
</template>
