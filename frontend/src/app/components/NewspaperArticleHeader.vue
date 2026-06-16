<script setup>
defineProps({
  section: {
    type: Object,
    required: true,
  },
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
  <div class="newspaper-article-head">
    <div>
      <p class="newspaper-kicker">{{ section.name }} · {{ article.source }}</p>
      <h1>{{ article.title }}</h1>
      <div class="newspaper-card-meta">
        <span v-if="article.published">{{ article.published }}</span>
        <span v-if="article.category">{{ article.category }}</span>
        <span v-if="article.author">By {{ article.author }}</span>
      </div>
    </div>
    <div class="newspaper-article-actions">
      <button class="ghost-button" type="button" @click="go('/newspaper')">返回英文小报</button>
      <a v-if="article.link" class="ghost-button" :href="article.link" target="_blank" rel="noreferrer">查看原文</a>
    </div>
  </div>
</template>
