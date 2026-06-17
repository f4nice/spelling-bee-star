<script setup>
import { booklearnerHeroActionsProps } from "../props/booklearnerHeroActionsProps.js";

defineProps(booklearnerHeroActionsProps);
</script>

<template>
  <div class="quote-head-actions">
    <button class="quote-more-link" type="button" @click="go('/booklearner')">首页</button>
    <button class="quote-more-link" type="button" @click="go('/booklearner/quotes')">更多</button>
    <button class="quote-more-link quote-upload-link" type="button" @click="go('/booklearner/upload')">上传</button>
  </div>
</template>
