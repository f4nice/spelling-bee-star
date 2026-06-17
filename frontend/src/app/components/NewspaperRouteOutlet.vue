<script setup>
import NewspaperArticlePage from "../pages/NewspaperArticlePage.vue";
import NewspaperPage from "../pages/NewspaperPage.vue";

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <NewspaperPage v-if="ctx.route.name === 'newspaper' && ctx.data" :data="ctx.data" :go="ctx.go" />
  <NewspaperArticlePage
    v-else-if="ctx.route.name === 'newspaperArticle' && ctx.data"
    :data="ctx.data"
    :go="ctx.go"
    :article-text="ctx.articleText"
  />
</template>
