<script setup>
import NewspaperArticleActions from "./NewspaperArticleActions.vue";
import NewspaperArticleDetailMeta from "./NewspaperArticleDetailMeta.vue";

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
      <NewspaperArticleDetailMeta :article="article" />
    </div>
    <NewspaperArticleActions :go="go" />
  </div>
</template>
