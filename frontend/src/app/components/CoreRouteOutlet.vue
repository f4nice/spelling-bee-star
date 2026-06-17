<script setup>
import ChallengeDayPage from "../pages/ChallengeDayPage.vue";
import HomePage from "../pages/HomePage.vue";
import ListDetailPage from "../pages/ListDetailPage.vue";
import ListsPage from "../pages/ListsPage.vue";
import NewspaperArticlePage from "../pages/NewspaperArticlePage.vue";
import NewspaperPage from "../pages/NewspaperPage.vue";
import WrongWordsPage from "../pages/WrongWordsPage.vue";

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <HomePage v-if="ctx.route.name === 'home' && ctx.data" :data="ctx.data" :go="ctx.go" :fallback-letter="ctx.fallbackLetter" />
  <ListsPage
    v-else-if="ctx.route.name === 'lists' && ctx.data"
    :data="ctx.data"
    :upload-options="ctx.uploadOptions"
    :upload-form="ctx.uploadForm"
    :batch-image-state="ctx.batchImageState"
    :submit-upload="ctx.submitUpload"
    :submit-batch-images="ctx.submitBatchImages"
    :fallback-letter="ctx.fallbackLetter"
    :go="ctx.go"
  />
  <ListDetailPage
    v-else-if="ctx.route.name === 'listDetail' && ctx.data"
    :data="ctx.data"
    :delete-list-state="ctx.deleteListState"
    :rename-list="ctx.renameList"
    :delete-list="ctx.deleteList"
    :sync-list-images="ctx.syncListImages"
    :word-detail-url="ctx.wordDetailUrl"
    :image-for-word="ctx.imageForWord"
    :fallback-letter="ctx.fallbackLetter"
    :go="ctx.go"
  />
  <NewspaperPage v-else-if="ctx.route.name === 'newspaper' && ctx.data" :data="ctx.data" :go="ctx.go" />
  <NewspaperArticlePage v-else-if="ctx.route.name === 'newspaperArticle' && ctx.data" :data="ctx.data" :go="ctx.go" :article-text="ctx.articleText" />
  <WrongWordsPage v-else-if="ctx.route.name === 'wrongWords' && ctx.data" :data="ctx.data" :go="ctx.go" />
  <ChallengeDayPage v-else-if="ctx.route.name === 'challengeDay' && ctx.data" :data="ctx.data" :go="ctx.go" :fallback-letter="ctx.fallbackLetter" />
</template>
