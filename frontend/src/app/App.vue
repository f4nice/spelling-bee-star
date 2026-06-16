<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import ChallengeApp from '../challenge/ChallengeApp.vue';
import HomePage from './pages/HomePage.vue';
import ListsPage from './pages/ListsPage.vue';
import ListDetailPage from './pages/ListDetailPage.vue';
import WordDetailPage from './pages/WordDetailPage.vue';
import UploadPage from './pages/UploadPage.vue';
import PreviewPage from './pages/PreviewPage.vue';
import NewspaperPage from './pages/NewspaperPage.vue';
import NewspaperArticlePage from './pages/NewspaperArticlePage.vue';
import BooklearnerPage from './pages/BooklearnerPage.vue';
import WrongWordsPage from './pages/WrongWordsPage.vue';
import ChallengeDayPage from './pages/ChallengeDayPage.vue';
import { useBooklearner } from './composables/useBooklearner.js';
import { useImportPreview } from './composables/useImportPreview.js';
import { useListTools } from './composables/useListTools.js';
import { useWordDetail } from './composables/useWordDetail.js';
import { oldPathFor, parseRoute, routeTitle as titleForRoute } from './router.js';
import { articleText, fallbackLetter, fetchJson, imageForWord, wordVueUrl } from './utils.js';

const route = ref(parseRoute());
const data = ref(null);
const loading = ref(false);
const error = ref('');

const routeTitle = computed(() => titleForRoute(route.value, data.value));
const legacyHref = computed(() => oldPathFor(window.location.pathname));

function setError(message) {
  error.value = message;
}

function go(path) {
  history.pushState(null, '', `/vue${path}`);
  route.value = parseRoute();
  loadRoute();
}

const {
  importForm,
  resetImportForm,
  setAllRows,
  setAllColumns,
  changePreviewSheet,
  submitImport,
} = useImportPreview({ data, route, go, loadRoute, setError });

const {
  wordEdit,
  imageCandidates,
  audioOptions,
  recorderState,
  resetWordTools,
  setWordEdit,
  saveWordField,
  refreshWord,
  uploadWordImage,
  findImages,
  chooseNetworkImage,
  playAudio,
  fetchAudioOptions,
  chooseAudio,
  startRecording,
  stopRecording,
  saveRecording,
  wordNavUrl,
  handleWordKeydown,
} = useWordDetail({ data, loadRoute });

const {
  book,
  loadBooklearner,
  analyzeBookQuery,
  analyzeBookText,
  analyzeBookFile,
  saveBookAnalysis,
  createBookWordList,
} = useBooklearner({ route, go });

const {
  uploadOptions,
  uploadForm,
  setUploadOptionsFromCards,
  loadUploadOptions,
  submitUpload,
  renameList,
  syncListImages,
} = useListTools({ data, go, loadRoute });

window.addEventListener('popstate', () => {
  route.value = parseRoute();
  loadRoute();
});

async function loadRoute() {
  if (route.value.name === 'challenge') {
    data.value = null;
    error.value = '';
    return;
  }
  loading.value = true;
  error.value = '';
  resetWordTools();
  try {
    if (route.value.name === 'home') data.value = await fetchJson('/api/vue/home');
    if (route.value.name === 'lists') {
      data.value = await fetchJson('/api/vue/lists');
      setUploadOptionsFromCards(data.value.cards);
    }
    if (route.value.name === 'listDetail') data.value = await fetchJson(`/api/vue/lists/${route.value.params.id}`);
    if (route.value.name === 'wrongWords') data.value = await fetchJson('/api/vue/wrong-words');
    if (route.value.name === 'challengeDay') data.value = await fetchJson(`/api/vue/challenge-calendar/${route.value.params.day}`);
    if (route.value.name === 'wordDetail') {
      data.value = await fetchJson(`/api/vue/words/${route.value.params.id}${window.location.search}`);
      setWordEdit(data.value.word);
    }
    if (route.value.name === 'upload') {
      await loadUploadOptions();
      data.value = { ok: true };
    }
    if (route.value.name === 'preview') {
      data.value = await fetchJson(`/api/vue/upload/preview/${route.value.params.id}${window.location.search}`);
      resetImportForm();
    }
    if (route.value.name === 'newspaper') data.value = await fetchJson('/api/vue/newspaper');
    if (route.value.name === 'newspaperArticle') data.value = await fetchJson(`/api/vue/newspaper/${route.value.params.section}/${route.value.params.index}`);
    if (route.value.name.startsWith('booklearner')) {
      data.value = { ok: true };
      await loadBooklearner();
    }
  } catch (err) {
    error.value = err.message || '页面数据加载失败';
  } finally {
    loading.value = false;
  }
}

function onKeydown(event) {
  handleWordKeydown(event, route.value);
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown);
  loadRoute();
});
onUnmounted(() => window.removeEventListener('keydown', onKeydown));
</script>

<template>
  <section class="panel vue-page-heading">
    <div>
      <p class="section-kicker">Vue App</p>
      <h1>{{ routeTitle }}</h1>
    </div>
    <nav class="vue-page-nav" aria-label="Vue 页面导航">
      <button type="button" class="secondary-button" @click="go('/')">首页</button>
      <button type="button" class="secondary-button" @click="go('/lists')">我的单词表</button>
      <button type="button" class="secondary-button" @click="go('/upload')">导入</button>
      <button type="button" class="secondary-button" @click="go('/newspaper')">英文小报</button>
      <button type="button" class="secondary-button" @click="go('/booklearner')">好词好句</button>
      <button type="button" class="secondary-button" @click="go('/wrong-words')">我的生词本</button>
      <a class="ghost-button" :href="legacyHref">返回旧版</a>
    </nav>
  </section>

  <div v-if="loading" class="empty-state">正在加载...</div>
  <div v-else-if="error" class="error-box">{{ error }}</div>

  <template v-else-if="route.name === 'challenge'">
    <div id="challenge-vue-app" :data-word-list-id="route.params.id">
      <ChallengeApp :word-list-id="route.params.id" />
    </div>
  </template>

  <HomePage v-else-if="route.name === 'home' && data" :data="data" :go="go" :fallback-letter="fallbackLetter" />
  <ListsPage v-else-if="route.name === 'lists' && data" :data="data" :upload-options="uploadOptions" :upload-form="uploadForm" :submit-upload="submitUpload" :fallback-letter="fallbackLetter" :go="go" />
  <ListDetailPage v-else-if="route.name === 'listDetail' && data" :data="data" :rename-list="renameList" :sync-list-images="syncListImages" :word-vue-url="wordVueUrl" :image-for-word="imageForWord" :fallback-letter="fallbackLetter" />
  <WordDetailPage v-else-if="route.name === 'wordDetail' && data" :data="data" :word-edit="wordEdit" :image-candidates="imageCandidates" :audio-options="audioOptions" :recorder-state="recorderState" :upload-word-image="uploadWordImage" :find-images="findImages" :choose-network-image="chooseNetworkImage" :word-nav-url="wordNavUrl" :save-word-field="saveWordField" :refresh-word="refreshWord" :play-audio="playAudio" :fetch-audio-options="fetchAudioOptions" :start-recording="startRecording" :choose-audio="chooseAudio" :stop-recording="stopRecording" :save-recording="saveRecording" :fallback-letter="fallbackLetter" />
  <UploadPage v-else-if="route.name === 'upload' && data" :upload-form="uploadForm" :upload-options="uploadOptions" :submit-upload="submitUpload" />
  <PreviewPage v-else-if="route.name === 'preview' && data" :data="data" :import-form="importForm" :go="go" :change-preview-sheet="changePreviewSheet" :set-all-rows="setAllRows" :set-all-columns="setAllColumns" :submit-import="submitImport" />
  <NewspaperPage v-else-if="route.name === 'newspaper' && data" :data="data" :go="go" />
  <NewspaperArticlePage v-else-if="route.name === 'newspaperArticle' && data" :data="data" :go="go" :article-text="articleText" />
  <BooklearnerPage v-else-if="route.name.startsWith('booklearner') && data" :route="route" :book="book" :go="go" :analyze-book-query="analyzeBookQuery" :analyze-book-text="analyzeBookText" :analyze-book-file="analyzeBookFile" :save-book-analysis="saveBookAnalysis" :create-book-word-list="createBookWordList" />
  <WrongWordsPage v-else-if="route.name === 'wrongWords' && data" :data="data" :go="go" />
  <ChallengeDayPage v-else-if="route.name === 'challengeDay' && data" :data="data" :go="go" :fallback-letter="fallbackLetter" />
</template>
