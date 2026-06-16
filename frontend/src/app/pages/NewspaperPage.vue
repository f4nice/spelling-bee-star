<script setup>
defineProps([
  "data",
  "go"
]);
</script>

<template>
    <section class="panel newspaper-hero"><div><p class="newspaper-kicker">China Daily Reader</p><h1>英文小报</h1><p>精选 China Daily 英文资讯，适合日常泛读和积累新闻表达。</p></div><a class="ghost-button" :href="data.source_url" target="_blank" rel="noreferrer">China Daily</a></section>
    <section class="newspaper-layout"><article v-for="section in data.sections" :key="section.key" class="panel newspaper-section"><div class="newspaper-section-head"><h2>{{ section.name }}</h2><span>{{ section.articles?.length || 0 }} articles</span></div><p v-if="section.error" class="newspaper-error">{{ section.error }}</p><div v-else class="newspaper-list"><button v-for="(article, index) in section.articles" :key="article.link || article.title" type="button" class="newspaper-card plain-card-button" :class="{ lead: index === 0, 'has-image': article.image_url }" @click="go(`/newspaper/${section.key}/${index}`)"><div v-if="article.image_url" class="newspaper-card-image"><img :src="article.image_url" :alt="article.title" loading="lazy"></div><div class="newspaper-card-content"><div class="newspaper-card-meta"><span>{{ article.source }}</span><span v-if="article.published">{{ article.published }}</span><span v-if="article.category">{{ article.category }}</span></div><h3>{{ article.title }}</h3><p>{{ article.summary || article.excerpt }}</p><small v-if="article.author">By {{ article.author }}</small></div></button></div></article></section>
</template>
