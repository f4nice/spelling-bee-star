<script setup>
import { defineAsyncComponent } from "vue";

const NewspaperArticlePage = defineAsyncComponent(() => import("../pages/NewspaperArticlePage.vue"));
const NewspaperPage = defineAsyncComponent(() => import("../pages/NewspaperPage.vue"));

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
