<script setup>
defineProps({
  article: {
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
  <div class="newspaper-article-actions">
    <button class="ghost-button" type="button" @click="go('/newspaper')">返回英文小报</button>
    <a v-if="article.link" class="ghost-button" :href="article.link" target="_blank" rel="noreferrer">查看原文</a>
  </div>
</template>
