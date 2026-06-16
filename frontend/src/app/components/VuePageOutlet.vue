<script setup>
import ChallengeApp from '../../challenge/ChallengeApp.vue';
import HomePage from '../pages/HomePage.vue';
import ListsPage from '../pages/ListsPage.vue';
import ListDetailPage from '../pages/ListDetailPage.vue';
import WordDetailPage from '../pages/WordDetailPage.vue';
import UploadPage from '../pages/UploadPage.vue';
import PreviewPage from '../pages/PreviewPage.vue';
import NewspaperPage from '../pages/NewspaperPage.vue';
import NewspaperArticlePage from '../pages/NewspaperArticlePage.vue';
import BooklearnerPage from '../pages/BooklearnerPage.vue';
import WrongWordsPage from '../pages/WrongWordsPage.vue';
import ChallengeDayPage from '../pages/ChallengeDayPage.vue';

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <template v-if="ctx.route.name === 'challenge'">
    <div id="challenge-vue-app" :data-word-list-id="ctx.route.params.id">
      <ChallengeApp :word-list-id="ctx.route.params.id" />
    </div>
  </template>

  <HomePage v-else-if="ctx.route.name === 'home' && ctx.data" :data="ctx.data" :go="ctx.go" :fallback-letter="ctx.fallbackLetter" />
  <ListsPage v-else-if="ctx.route.name === 'lists' && ctx.data" :data="ctx.data" :upload-options="ctx.uploadOptions" :upload-form="ctx.uploadForm" :submit-upload="ctx.submitUpload" :fallback-letter="ctx.fallbackLetter" :go="ctx.go" />
  <ListDetailPage v-else-if="ctx.route.name === 'listDetail' && ctx.data" :data="ctx.data" :rename-list="ctx.renameList" :sync-list-images="ctx.syncListImages" :word-vue-url="ctx.wordVueUrl" :image-for-word="ctx.imageForWord" :fallback-letter="ctx.fallbackLetter" />
  <WordDetailPage v-else-if="ctx.route.name === 'wordDetail' && ctx.data" :data="ctx.data" :word-edit="ctx.wordEdit" :image-candidates="ctx.imageCandidates" :audio-options="ctx.audioOptions" :recorder-state="ctx.recorderState" :upload-word-image="ctx.uploadWordImage" :find-images="ctx.findImages" :choose-network-image="ctx.chooseNetworkImage" :word-nav-url="ctx.wordNavUrl" :save-word-field="ctx.saveWordField" :refresh-word="ctx.refreshWord" :play-audio="ctx.playAudio" :fetch-audio-options="ctx.fetchAudioOptions" :start-recording="ctx.startRecording" :choose-audio="ctx.chooseAudio" :stop-recording="ctx.stopRecording" :save-recording="ctx.saveRecording" :fallback-letter="ctx.fallbackLetter" />
  <UploadPage v-else-if="ctx.route.name === 'upload' && ctx.data" :upload-form="ctx.uploadForm" :upload-options="ctx.uploadOptions" :submit-upload="ctx.submitUpload" />
  <PreviewPage v-else-if="ctx.route.name === 'preview' && ctx.data" :data="ctx.data" :import-form="ctx.importForm" :go="ctx.go" :change-preview-sheet="ctx.changePreviewSheet" :set-all-rows="ctx.setAllRows" :set-all-columns="ctx.setAllColumns" :submit-import="ctx.submitImport" />
  <NewspaperPage v-else-if="ctx.route.name === 'newspaper' && ctx.data" :data="ctx.data" :go="ctx.go" />
  <NewspaperArticlePage v-else-if="ctx.route.name === 'newspaperArticle' && ctx.data" :data="ctx.data" :go="ctx.go" :article-text="ctx.articleText" />
  <BooklearnerPage v-else-if="ctx.route.name.startsWith('booklearner') && ctx.data" :route="ctx.route" :book="ctx.book" :go="ctx.go" :analyze-book-query="ctx.analyzeBookQuery" :analyze-book-text="ctx.analyzeBookText" :analyze-book-file="ctx.analyzeBookFile" :save-book-analysis="ctx.saveBookAnalysis" :create-book-word-list="ctx.createBookWordList" />
  <WrongWordsPage v-else-if="ctx.route.name === 'wrongWords' && ctx.data" :data="ctx.data" :go="ctx.go" />
  <ChallengeDayPage v-else-if="ctx.route.name === 'challengeDay' && ctx.data" :data="ctx.data" :go="ctx.go" :fallback-letter="ctx.fallbackLetter" />
</template>
