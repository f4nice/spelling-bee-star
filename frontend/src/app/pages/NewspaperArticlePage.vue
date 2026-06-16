<script setup>
defineProps([
  "data",
  "go",
  "articleText"
]);
</script>

<template>
    <section class="panel newspaper-article"><div class="newspaper-article-head"><div><p class="newspaper-kicker">{{ data.section.name }} · {{ data.article.source }}</p><h1>{{ data.article.title }}</h1><div class="newspaper-card-meta"><span v-if="data.article.published">{{ data.article.published }}</span><span v-if="data.article.category">{{ data.article.category }}</span><span v-if="data.article.author">By {{ data.article.author }}</span></div></div><div class="newspaper-article-actions"><button class="ghost-button" type="button" @click="go('/newspaper')">返回英文小报</button><a v-if="data.article.link" class="ghost-button" :href="data.article.link" target="_blank" rel="noreferrer">查看原文</a></div></div><figure v-if="data.article.image_url" class="newspaper-article-image"><img :src="data.article.image_url" :alt="data.article.title"></figure><p v-if="data.article.summary" class="newspaper-article-summary">{{ data.article.summary }}</p><article class="newspaper-article-body"><p v-for="(paragraph, index) in articleText(data.article)" :key="index">{{ paragraph }}</p></article></section>
</template>
