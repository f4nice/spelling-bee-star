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
import { oldPathFor, parseRoute, routeTitle as titleForRoute } from './router.js';
import { articleText, fallbackLetter, fetchJson, imageForWord, wordVueUrl } from './utils.js';

const route = ref(parseRoute());
const data = ref(null);
const loading = ref(false);
const error = ref('');
const uploadOptions = ref({ word_lists: [] });
const uploadForm = ref({ word_list_id: '', word_list_name: '', file: null });
const importForm = ref({ word_list_name: '', word_columns: [], selected_rows: [], selected_columns: [], image_files: [] });
const wordEdit = ref({});
const wordSaving = ref('');
const imageCandidates = ref([]);
const audioOptions = ref({ us: [], gb: [] });
const recorderState = ref({ accent: '', status: '', blob: null, preview: '' });
const book = ref({ query: '', title: '', author: '', text: '', file: null, result: null, history: [], featured: [], suggestions: [], notice: '' });
let mediaRecorder = null;
let mediaStream = null;
let mediaChunks = [];

window.addEventListener('popstate', () => {
  route.value = parseRoute();
  loadRoute();
});

const routeTitle = computed(() => titleForRoute(route.value, data.value));
const legacyHref = computed(() => oldPathFor(window.location.pathname));

function go(path) {
  history.pushState(null, '', `/vue${path}`);
  route.value = parseRoute();
  loadRoute();
}


async function loadRoute() {
  if (route.value.name === 'challenge') {
    data.value = null;
    error.value = '';
    return;
  }
  loading.value = true;
  error.value = '';
  imageCandidates.value = [];
  audioOptions.value = { us: [], gb: [] };
  try {
    if (route.value.name === 'home') data.value = await fetchJson('/api/vue/home');
    if (route.value.name === 'lists') {
      data.value = await fetchJson('/api/vue/lists');
      uploadOptions.value = { word_lists: data.value.cards.map((card) => card.list) };
    }
    if (route.value.name === 'listDetail') data.value = await fetchJson(`/api/vue/lists/${route.value.params.id}`);
    if (route.value.name === 'wrongWords') data.value = await fetchJson('/api/vue/wrong-words');
    if (route.value.name === 'challengeDay') data.value = await fetchJson(`/api/vue/challenge-calendar/${route.value.params.day}`);
    if (route.value.name === 'wordDetail') {
      data.value = await fetchJson(`/api/vue/words/${route.value.params.id}${window.location.search}`);
      wordEdit.value = {
        alternate_spellings: data.value.word.alternate_spellings || '',
        english_definition: data.value.word.english_definition || '',
        chinese_definition: data.value.word.chinese_definition || '',
        english_example: data.value.word.english_example || '',
      };
    }
    if (route.value.name === 'upload') {
      uploadOptions.value = await fetchJson('/api/vue/upload/options');
      data.value = { ok: true };
    }
    if (route.value.name === 'preview') {
      data.value = await fetchJson(`/api/vue/upload/preview/${route.value.params.id}${window.location.search}`);
      resetImportForm();
    }
    if (route.value.name === 'newspaper') data.value = await fetchJson('/api/vue/newspaper');
    if (route.value.name === 'newspaperArticle') data.value = await fetchJson(`/api/vue/newspaper/${route.value.params.section}/${route.value.params.index}`);
    if (route.value.name.startsWith('booklearner')) await loadBooklearner();
  } catch (err) {
    error.value = err.message || '页面数据加载失败';
  } finally {
    loading.value = false;
  }
}

async function submitUpload() {
  if (!uploadForm.value.file) return;
  const form = new FormData();
  form.append('file', uploadForm.value.file);
  form.append('word_list_id', uploadForm.value.word_list_id || '');
  form.append('word_list_name', uploadForm.value.word_list_name || '');
  const result = await fetchJson('/api/vue/upload', { method: 'POST', body: form });
  go(`/upload/preview/${result.preview_id}`);
}

function resetImportForm() {
  const preview = data.value?.preview;
  if (!preview) return;
  importForm.value = {
    word_list_name: preview.word_list_name || '',
    word_columns: [...(preview.inferred_word_columns || [preview.inferred_word_column].filter(Boolean))],
    selected_rows: preview.rows.map((row) => row.index),
    selected_columns: [...preview.columns],
    image_files: [],
  };
}

function setAllRows(checked) {
  importForm.value.selected_rows = checked ? data.value.preview.rows.map((row) => row.index) : [];
}

function setAllColumns(checked) {
  importForm.value.selected_columns = checked ? [...data.value.preview.columns] : [];
}

async function changePreviewSheet(sheetName) {
  const params = new URLSearchParams({
    sheet_name: sheetName,
    word_list_name: importForm.value.word_list_name || data.value.preview.word_list_name || '',
    word_list_id: data.value.preview.word_list_id || '',
  });
  history.replaceState(null, '', `/vue/upload/preview/${route.value.params.id}?${params.toString()}`);
  await loadRoute();
}

async function submitImport() {
  if (!importForm.value.word_columns.length) {
    error.value = '请至少选择一个英文单词列';
    return;
  }
  const form = new FormData();
  form.append('preview_id', route.value.params.id);
  form.append('word_list_id', data.value.preview.word_list_id || '');
  form.append('word_list_name', importForm.value.word_list_name);
  importForm.value.word_columns.forEach((item) => form.append('word_columns', item));
  importForm.value.selected_rows.forEach((item) => form.append('selected_rows', item));
  importForm.value.selected_columns.forEach((item) => form.append('selected_columns', item));
  importForm.value.image_files.forEach((item) => form.append('image_files', item));
  const result = await fetchJson('/api/vue/import-preview', { method: 'POST', body: form });
  go(`/lists/${result.word_list_id}`);
}

async function renameList() {
  const form = new FormData();
  form.append('name', data.value.word_list.name);
  await fetchJson(`/lists/${data.value.word_list.id}/rename`, { method: 'POST', body: form, headers: { 'x-requested-with': 'fetch' } });
}

async function syncListImages() {
  const job = await fetchJson(`/lists/${data.value.word_list.id}/sync-images/start`, { method: 'POST' });
  data.value.sync_job = job;
  const timer = window.setInterval(async () => {
    const next = await fetchJson(`/lists/${data.value.word_list.id}/sync-images/${job.id}`);
    data.value.sync_job = next;
    if (['done', 'failed'].includes(next.status)) {
      window.clearInterval(timer);
      await loadRoute();
    }
  }, 1200);
}

async function saveWordField(field) {
  wordSaving.value = field;
  const form = new FormData();
  form.append('edit_token', '1');
  form.append('field', field);
  form.append('value', wordEdit.value[field] || '');
  try {
    const result = await fetchJson(`/api/vue/words/${data.value.word.id}/field`, { method: 'POST', body: form });
    data.value.word[field] = result.value;
  } finally {
    wordSaving.value = '';
  }
}

async function refreshWord() {
  const form = new FormData();
  form.append('edit_token', '1');
  await fetchJson(`/api/vue/words/${data.value.word.id}/refresh`, { method: 'POST', body: form });
  await loadRoute();
}

async function uploadWordImage(file) {
  const form = new FormData();
  form.append('edit_token', '1');
  form.append('file', file);
  await fetch(`/words/${data.value.word.id}/image`, { method: 'POST', body: form });
  await loadRoute();
}

async function findImages() {
  const form = new FormData();
  form.append('edit_token', '1');
  const result = await fetchJson(`/words/${data.value.word.id}/image-candidates`, { method: 'POST', body: form });
  imageCandidates.value = result.images || [];
}

async function chooseNetworkImage(url) {
  const form = new FormData();
  form.append('edit_token', '1');
  form.append('image_url', url);
  await fetchJson(`/words/${data.value.word.id}/network-image`, { method: 'POST', body: form });
  await loadRoute();
}

function playAudio(id) {
  const audio = document.getElementById(id);
  if (!audio) return;
  audio.load();
  audio.currentTime = 0;
  audio.play().catch(() => { audio.controls = true; });
}

async function fetchAudioOptions(accent) {
  const form = new FormData();
  form.append('edit_token', '1');
  form.append('accent', accent);
  const result = await fetchJson(`/words/${data.value.word.id}/audio-options`, { method: 'POST', body: form });
  audioOptions.value[accent] = result.options || [];
}

async function chooseAudio(accent, url) {
  const form = new FormData();
  form.append('edit_token', '1');
  form.append('accent', accent);
  form.append('audio_url', url);
  await fetchJson(`/words/${data.value.word.id}/audio-choice`, { method: 'POST', body: form });
  await loadRoute();
}

async function startRecording(accent) {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    recorderState.value = { accent, status: '当前浏览器不支持在线录音，或需要 HTTPS 后才能使用麦克风。', blob: null, preview: '' };
    return;
  }
  mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaChunks = [];
  mediaRecorder = new MediaRecorder(mediaStream);
  mediaRecorder.addEventListener('dataavailable', (event) => {
    if (event.data?.size) mediaChunks.push(event.data);
  });
  mediaRecorder.addEventListener('stop', () => {
    const blob = new Blob(mediaChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
    recorderState.value = { accent, status: '录音完成，可以先回听，再确认替换。', blob, preview: URL.createObjectURL(blob) };
    mediaStream?.getTracks().forEach((track) => track.stop());
  });
  recorderState.value = { accent, status: '录音中...', blob: null, preview: '' };
  mediaRecorder.start();
}

function stopRecording() {
  if (mediaRecorder?.state === 'recording') mediaRecorder.stop();
}

async function saveRecording() {
  if (!recorderState.value.blob) return;
  const form = new FormData();
  form.append('edit_token', '1');
  form.append('accent', recorderState.value.accent);
  form.append('audio_file', recorderState.value.blob, `recorded-${recorderState.value.accent}.webm`);
  await fetchJson(`/words/${data.value.word.id}/recorded-audio`, { method: 'POST', body: form });
  recorderState.value = { accent: '', status: '录音已保存', blob: null, preview: '' };
  await loadRoute();
}

function wordNavUrl(wordId) {
  const params = new URLSearchParams(window.location.search);
  params.set('edit', '1');
  return `/vue/words/${wordId}?${params.toString()}`;
}

function onKeydown(event) {
  if (route.value.name !== 'wordDetail' || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
  const active = document.activeElement;
  if (active?.matches('input, textarea, select, button, audio') || active?.isContentEditable) return;
  const nav = data.value?.navigation;
  if (!nav) return;
  window.location.href = wordNavUrl(event.key === 'ArrowLeft' ? nav.previous_word_id : nav.next_word_id);
}

async function loadBooklearner() {
  data.value = { ok: true };
  if (route.value.name === 'booklearnerDetail') {
    book.value.result = await fetchJson(`/booklearner/api/history/${route.value.params.id}`);
    book.value.featured = (await fetchJson(`/booklearner/api/featured?limit=80&analysis_id=${route.value.params.id}`)).items || [];
    return;
  }
  const limit = route.value.name === 'booklearnerQuotes' ? 40 : 12;
  book.value.featured = (await fetchJson(`/booklearner/api/featured?limit=${limit}`)).items || [];
  book.value.history = (await fetchJson('/booklearner/api/history')).items || [];
}

async function analyzeBookQuery() {
  book.value.notice = '正在分析...';
  book.value.result = await fetchJson(`/booklearner/api/analyze?q=${encodeURIComponent(book.value.query)}`);
  book.value.notice = '分析完成';
}

async function analyzeBookText() {
  book.value.notice = '正在分析文本...';
  book.value.result = await fetchJson('/booklearner/api/analyze-text', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ title: book.value.title, author: book.value.author, text: book.value.text }),
  });
  book.value.notice = '分析完成';
}

async function analyzeBookFile() {
  if (!book.value.file) return;
  const form = new FormData();
  form.append('title', book.value.title);
  form.append('author', book.value.author);
  form.append('file', book.value.file);
  book.value.notice = '正在分析文件...';
  book.value.result = await fetchJson('/booklearner/api/analyze-file', { method: 'POST', body: form });
  book.value.notice = '分析完成';
}

async function saveBookAnalysis() {
  const result = await fetchJson('/booklearner/api/save-analysis', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query: book.value.query || book.value.title, result: book.value.result }),
  });
  book.value.notice = `已保存 #${result.storage?.id || ''}`;
}

async function createBookWordList() {
  const vocabulary = book.value.result?.vocabulary || book.value.result?.words || [];
  const result = await fetchJson('/booklearner/api/word-list', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ title: book.value.result?.book?.title || book.value.title || 'BookLearner 单词表', vocabulary }),
  });
  go(`/lists/${result.word_list_id}`);
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

  <template v-else-if="route.name === 'home' && data">
    <HomePage :data="data" :go="go" :fallback-letter="fallbackLetter" />
  </template>

  <template v-else-if="route.name === 'lists' && data">
    <ListsPage :data="data" :upload-options="uploadOptions" :upload-form="uploadForm" :submit-upload="submitUpload" :fallback-letter="fallbackLetter" :go="go" />
  </template>

  <template v-else-if="route.name === 'listDetail' && data">
    <ListDetailPage :data="data" :rename-list="renameList" :sync-list-images="syncListImages" :word-vue-url="wordVueUrl" :image-for-word="imageForWord" :fallback-letter="fallbackLetter" />
  </template>

  <template v-else-if="route.name === 'wordDetail' && data">
    <WordDetailPage :data="data" :word-edit="wordEdit" :image-candidates="imageCandidates" :audio-options="audioOptions" :recorder-state="recorderState" :upload-word-image="uploadWordImage" :find-images="findImages" :choose-network-image="chooseNetworkImage" :word-nav-url="wordNavUrl" :save-word-field="saveWordField" :refresh-word="refreshWord" :play-audio="playAudio" :fetch-audio-options="fetchAudioOptions" :start-recording="startRecording" :choose-audio="chooseAudio" :stop-recording="stopRecording" :save-recording="saveRecording" :fallback-letter="fallbackLetter" />
  </template>

  <template v-else-if="route.name === 'upload' && data">
    <UploadPage :upload-form="uploadForm" :upload-options="uploadOptions" :submit-upload="submitUpload" />
  </template>

  <template v-else-if="route.name === 'preview' && data">
    <PreviewPage :data="data" :import-form="importForm" :go="go" :change-preview-sheet="changePreviewSheet" :set-all-rows="setAllRows" :set-all-columns="setAllColumns" :submit-import="submitImport" />
  </template>

  <template v-else-if="route.name === 'newspaper' && data">
    <NewspaperPage :data="data" :go="go" />
  </template>

  <template v-else-if="route.name === 'newspaperArticle' && data">
    <NewspaperArticlePage :data="data" :go="go" :article-text="articleText" />
  </template>

  <template v-else-if="route.name.startsWith('booklearner') && data">
    <BooklearnerPage :route="route" :book="book" :go="go" :analyze-book-query="analyzeBookQuery" :analyze-book-text="analyzeBookText" :analyze-book-file="analyzeBookFile" :save-book-analysis="saveBookAnalysis" :create-book-word-list="createBookWordList" />
  </template>

  <template v-else-if="route.name === 'wrongWords' && data">
    <WrongWordsPage :data="data" :go="go" />
  </template>

  <template v-else-if="route.name === 'challengeDay' && data">
    <ChallengeDayPage :data="data" :go="go" :fallback-letter="fallbackLetter" />
  </template>
</template>
