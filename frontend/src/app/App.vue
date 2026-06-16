<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import ChallengeApp from '../challenge/ChallengeApp.vue';

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

const routeTitle = computed(() => {
  if (route.value.name === 'lists') return '我的单词表';
  if (route.value.name === 'listDetail') return data.value?.word_list?.name || '单词表';
  if (route.value.name === 'wrongWords') return '我的生词本';
  if (route.value.name === 'challengeDay') return `${route.value.params.day} 挑战词汇`;
  if (route.value.name === 'challenge') return 'Vue 挑战';
  if (route.value.name === 'wordDetail') return data.value?.word?.word || '单词详情';
  if (route.value.name === 'upload') return '导入单词';
  if (route.value.name === 'preview') return '导入预览';
  if (route.value.name === 'newspaper') return '英文小报';
  if (route.value.name === 'newspaperArticle') return data.value?.article?.title || '英文小报';
  if (route.value.name.startsWith('booklearner')) return '好词好句';
  return '今天从这里开始';
});
const legacyHref = computed(() => oldPathFor(window.location.pathname));

function parseRoute() {
  const path = window.location.pathname.replace(/^\/vue\/?/, '').replace(/\/$/, '');
  const parts = path ? path.split('/') : [];
  if (!parts.length) return { name: 'home', params: {} };
  if (parts[0] === 'lists' && parts[1]) return { name: 'listDetail', params: { id: Number(parts[1]) } };
  if (parts[0] === 'lists') return { name: 'lists', params: {} };
  if (parts[0] === 'wrong-words') return { name: 'wrongWords', params: {} };
  if (parts[0] === 'challenge-calendar' && parts[1]) return { name: 'challengeDay', params: { day: parts[1] } };
  if (parts[0] === 'challenge' && parts[1]) return { name: 'challenge', params: { id: Number(parts[1]) } };
  if (parts[0] === 'words' && parts[1]) return { name: 'wordDetail', params: { id: Number(parts[1]) } };
  if (parts[0] === 'upload' && parts[1] === 'preview' && parts[2]) return { name: 'preview', params: { id: parts[2] } };
  if (parts[0] === 'upload') return { name: 'upload', params: {} };
  if (parts[0] === 'newspaper' && parts[1] && parts[2]) return { name: 'newspaperArticle', params: { section: parts[1], index: Number(parts[2]) } };
  if (parts[0] === 'newspaper') return { name: 'newspaper', params: {} };
  if (parts[0] === 'booklearner' && parts[1] === 'upload') return { name: 'booklearnerUpload', params: {} };
  if (parts[0] === 'booklearner' && parts[1] === 'quotes') return { name: 'booklearnerQuotes', params: {} };
  if (parts[0] === 'booklearner' && parts[1] === 'detail' && parts[2]) return { name: 'booklearnerDetail', params: { id: Number(parts[2]) } };
  if (parts[0] === 'booklearner') return { name: 'booklearner', params: {} };
  return { name: 'home', params: {} };
}

function go(path) {
  history.pushState(null, '', `/vue${path}`);
  route.value = parseRoute();
  loadRoute();
}

function oldPathFor(path) {
  return path.replace(/^\/vue/, '') || '/';
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const isJson = response.headers.get('content-type')?.includes('application/json');
  const payload = isJson ? await response.json() : null;
  if (!response.ok) throw new Error(payload?.detail || payload?.error || '页面数据加载失败');
  return payload;
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

function imageForWord(word) {
  return word?.image_url || '';
}

function fallbackLetter(word) {
  return (word?.word || '?').slice(0, 1).toUpperCase();
}

function wordVueUrl(word, listId = null) {
  const params = new URLSearchParams();
  params.set('edit', '1');
  if (listId) params.set('list_id', listId);
  return `/vue/words/${word.id}?${params.toString()}`;
}

function articleText(article) {
  return String(article?.body || article?.excerpt || article?.summary || '').split('\n').filter((item) => item.trim());
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
    <section class="home-stats-grid">
      <button class="home-stat-card panel" type="button" @click="go('/lists')"><span>我的单词表</span><strong>{{ data.stats.word_lists }}</strong><small>{{ data.stats.words }} 个单词</small></button>
      <button class="home-stat-card panel" type="button" @click="go('/newspaper')"><span>英文小报</span><strong>Today</strong><small>China Daily 今日泛读</small></button>
      <button class="home-stat-card panel" type="button" @click="go('/booklearner')"><span>好词好句</span><strong>Books</strong><small>书摘与难点词</small></button>
      <button class="home-stat-card panel" type="button" @click="go('/wrong-words')"><span>我的生词本</span><strong>{{ data.stats.wrong_words }}</strong><small>今日 {{ data.stats.today_wrong_count }} 个</small></button>
    </section>
    <section class="panel calendar-panel home-calendar">
      <div class="calendar-heading"><div><p class="section-kicker">Challenge</p><h2>挑战日历</h2><p>{{ data.calendar.title }} · 本月答对 {{ data.calendar.month_correct }} 个，答错 {{ data.calendar.month_wrong }} 个</p></div></div>
      <div class="challenge-calendar">
        <div v-for="weekday in data.calendar.weekdays" :key="weekday" class="calendar-weekday">{{ weekday }}</div>
        <template v-for="(week, weekIndex) in data.calendar.weeks" :key="weekIndex">
          <button v-for="(day, dayIndex) in week" :key="`${weekIndex}-${dayIndex}`" type="button" class="calendar-day" :class="{ today: day.is_today, empty: !day.day, 'has-records': day.total }" :disabled="!day.total" @click="day.total && go(`/challenge-calendar/${day.date}`)">
            <span v-if="day.day" class="calendar-day-number">{{ day.day }}</span><span v-if="day.total" class="calendar-total">{{ day.total }} 个</span>
          </button>
        </template>
      </div>
    </section>
    <section class="home-section-head"><div><p class="section-kicker">Lists</p><h2>我的单词表</h2></div><button class="ghost-button" type="button" @click="go('/lists')">全部单词表</button></section>
    <section class="word-grid home-list-grid">
      <article v-for="card in data.featured_cards" :key="card.list.id" class="word-card list-card">
        <button class="list-card-link plain-card-button" type="button" @click="go(`/lists/${card.list.id}`)">
          <img v-if="card.cover_word?.image_url" :src="card.cover_word.image_url" :alt="card.list.name"><div v-else class="image-fallback">{{ fallbackLetter(card.cover_word) }}</div>
          <div class="word-card-body"><div class="word-card-title"><strong>{{ card.list.name }}</strong><span class="status">{{ card.count }} 词</span></div></div>
        </button>
      </article>
    </section>
  </template>

  <template v-else-if="route.name === 'lists' && data">
    <section class="panel lists-tools-panel">
      <div class="lists-tool-card">
        <div class="lists-import-heading"><p class="section-kicker">Import</p><h2>新增单词表</h2></div>
        <form class="home-upload-form lists-import-form" @submit.prevent="submitUpload">
          <input v-model="uploadForm.word_list_name" type="text" placeholder="单词表名称" required>
          <select v-model="uploadForm.word_list_id"><option value="">新建单词表</option><option v-for="list in uploadOptions.word_lists" :key="list.id" :value="list.id">{{ list.name }}</option></select>
          <input type="file" accept=".xlsx,.xlsm,.xltx,.xltm" required @change="uploadForm.file = $event.target.files[0]">
          <button type="submit">上传预览</button>
        </form>
      </div>
      <div class="lists-tool-card">
        <div class="lists-import-heading"><p class="section-kicker">Images</p><h2>批量上传图片</h2><p>按序号或英文名自动匹配单词。</p></div>
        <form action="/lists/batch-images" method="post" enctype="multipart/form-data" class="home-upload-form batch-image-form">
          <select name="word_list_id" required><option value="">选择单词表</option><option v-for="card in data.cards" :key="card.list.id" :value="card.list.id">{{ card.list.name }}</option></select>
          <input type="file" name="image_files" accept="image/*" multiple webkitdirectory directory required>
          <button type="submit">上传匹配</button>
        </form>
      </div>
    </section>
    <section class="word-grid">
      <article v-for="card in data.cards" :key="card.list.id" class="word-card list-card">
        <button class="list-card-link plain-card-button" type="button" @click="go(`/lists/${card.list.id}`)">
          <img v-if="card.cover_word?.image_url" :src="card.cover_word.image_url" :alt="card.list.name"><div v-else class="image-fallback">{{ fallbackLetter(card.cover_word) }}</div>
          <div class="word-card-body"><div class="word-card-title"><strong>{{ card.list.name }}</strong><span class="status">{{ card.count }} 词</span></div></div>
        </button>
        <div class="challenge-card-actions">
          <div class="mini-progress"><span>{{ card.challenge.completed }} / {{ card.challenge.total }}</span><div><i :style="{ width: `${card.challenge.percent}%` }"></i></div></div>
          <button class="challenge-button" type="button" @click="go(`/challenge/${card.list.id}?daily_count=20&start_count=${card.challenge.completed}`)">Vue挑战</button>
        </div>
      </article>
    </section>
  </template>

  <template v-else-if="route.name === 'listDetail' && data">
    <section class="panel upload-panel">
      <div><input v-model="data.word_list.name" class="list-title-input"><p>{{ data.words.length }} 个单词</p></div>
      <div class="list-actions"><button class="secondary-button" type="button" @click="renameList">保存名称</button><a class="ghost-button compact-button" href="/vue/upload">继续导入</a><form :action="`/lists/${data.word_list.id}/delete`" method="post" class="delete-list-form"><input type="password" name="password" placeholder="删除密码" required><button class="danger-button" type="submit">删除</button></form></div>
    </section>
    <section class="panel image-sync-panel">
      <div class="sync-summary"><div class="sync-heading"><strong>图片同步</strong><span v-if="data.sync_job">{{ data.sync_job.done }} / {{ data.sync_job.total }}</span></div><p>{{ data.sync_job?.message || '查找缺失图片，下载并压缩到服务器图片库。' }}</p></div>
      <button class="secondary-button sync-image-button" type="button" @click="syncListImages">同步图片</button>
    </section>
    <section class="word-grid">
      <a v-for="(word, index) in data.words" :key="word.id" class="word-card" :href="wordVueUrl(word, data.word_list.id)">
        <span class="word-index-badge">#{{ index + 1 }}</span><img v-if="imageForWord(word)" :src="word.image_url" :alt="word.word"><div v-else class="image-fallback">{{ fallbackLetter(word) }}</div>
        <div class="word-card-body"><div class="word-card-title"><strong>{{ word.word }}</strong><span class="challenge-result-badges"><span class="challenge-result-badge is-correct">对 {{ word.challenge_stats.correct }}</span><span class="challenge-result-badge is-wrong">错 {{ word.challenge_stats.wrong }}</span></span></div><p>{{ word.chinese_definition || word.english_definition || '等待补全' }}</p></div>
      </a>
    </section>
  </template>

  <template v-else-if="route.name === 'wordDetail' && data">
    <section class="detail-layout">
      <div class="detail-media-panel">
        <div class="detail-media"><span v-if="data.navigation.index" class="word-index-badge">#{{ data.navigation.index }}</span><img v-if="data.word.image_url" :src="data.word.image_url" :alt="data.word.word"><div v-else class="image-fallback large">{{ fallbackLetter(data.word) }}</div></div>
        <div v-if="data.can_edit" class="image-replace-form">
          <label>替换图片 <input type="file" accept="image/*" @change="$event.target.files[0] && uploadWordImage($event.target.files[0])"></label>
          <button type="button" class="secondary-button" @click="findImages">网络找图</button>
          <span v-if="data.word.image_locked" class="lock-badge">已锁定</span>
        </div>
        <div v-if="imageCandidates.length" class="image-picker-grid inline-image-grid">
          <button v-for="(item, index) in imageCandidates" :key="item.url" type="button" class="image-picker-option" @click="chooseNetworkImage(item.url)"><img :src="item.url" :alt="`候选图 ${index + 1}`"><span>{{ item.source || '网络图片' }}</span></button>
        </div>
      </div>
      <article class="panel detail-panel">
        <div class="detail-study-row"><div class="auto-study-controls"><a class="secondary-button" :href="wordNavUrl(data.navigation.previous_word_id)">上一个</a><a class="secondary-button" :href="wordNavUrl(data.navigation.next_word_id)">下一个</a></div></div>
        <div class="detail-heading"><div class="word-title-stack"><h1>{{ data.word.word }}</h1><p v-if="data.word.phonetic" class="phonetic">/{{ data.word.phonetic }}/</p><textarea v-if="data.can_edit" v-model="wordEdit.alternate_spellings" class="inline-edit-input" @blur="saveWordField('alternate_spellings')"></textarea><strong v-else>{{ data.word.alternate_spellings || '暂无' }}</strong></div><div class="detail-heading-actions"><button v-if="data.can_edit" type="button" @click="refreshWord">重新补全</button></div></div>
        <div class="audio-row">
          <label v-for="accent in ['us','gb']" :key="accent">{{ accent === 'us' ? '美式发音' : '英式发音' }}
            <div class="audio-actions"><button type="button" class="secondary-button" @click="playAudio(`audio-${accent}`)">朗读{{ accent === 'us' ? '美式' : '英式' }}</button><audio :id="`audio-${accent}`" controls preload="none" :src="data.audio_sources[accent]"></audio><button v-if="data.can_edit" type="button" class="secondary-button" @click="fetchAudioOptions(accent)">重新获取音频</button><button v-if="data.can_edit" type="button" class="secondary-button" @click="startRecording(accent)">录制音源</button></div>
            <div v-if="audioOptions[accent]?.length" class="audio-options"><div v-for="option in audioOptions[accent]" :key="option.url" class="audio-option"><strong>{{ option.label }}</strong><audio controls :src="option.url"></audio><button type="button" class="secondary-button" @click="chooseAudio(accent, option.url)">选这个</button></div></div>
          </label>
        </div>
        <div v-if="recorderState.status" class="record-audio-panel"><p>{{ recorderState.status }}</p><button type="button" class="secondary-button" @click="stopRecording">停止录音</button><audio v-if="recorderState.preview" controls :src="recorderState.preview"></audio><button v-if="recorderState.blob" type="button" @click="saveRecording">确认替换</button></div>
        <dl class="definition-list">
          <dt>词性</dt><dd>{{ data.word.part_of_speech || '暂无' }}</dd>
          <dt>英文定义</dt><dd><textarea v-if="data.can_edit" v-model="wordEdit.english_definition" @blur="saveWordField('english_definition')"></textarea><span v-else>{{ data.word.english_definition || '暂无' }}</span></dd>
          <dt>中文定义</dt><dd><textarea v-if="data.can_edit" v-model="wordEdit.chinese_definition" @blur="saveWordField('chinese_definition')"></textarea><span v-else>{{ data.word.chinese_definition || '暂无' }}</span></dd>
          <dt>英文例句</dt><dd><textarea v-if="data.can_edit" v-model="wordEdit.english_example" @blur="saveWordField('english_example')"></textarea><span v-else>{{ data.word.english_example || '暂无' }}</span></dd>
          <dt>来源</dt><dd>{{ data.word.source || '暂无' }}</dd>
        </dl>
        <div v-if="data.word.enrichment_error" class="error-box">{{ data.word.enrichment_error }}</div>
      </article>
    </section>
  </template>

  <template v-else-if="route.name === 'upload' && data">
    <section class="panel upload-panel"><div><h1>导入 Excel</h1><p>上传后会进入 Vue 预览页，可以选择行、列和单词列。</p></div></section>
    <form class="panel upload-form wide-form" @submit.prevent="submitUpload">
      <label>单词表名称 <input v-model="uploadForm.word_list_name" required></label>
      <label>已有单词表 <select v-model="uploadForm.word_list_id"><option value="">新建单词表</option><option v-for="list in uploadOptions.word_lists" :key="list.id" :value="list.id">{{ list.name }}</option></select></label>
      <label>Excel 文件 <input type="file" accept=".xlsx,.xlsm,.xltx,.xltm" required @change="uploadForm.file = $event.target.files[0]"></label>
      <button type="submit">上传预览</button>
    </form>
  </template>

  <template v-else-if="route.name === 'preview' && data">
    <section class="panel preview-panel">
      <div class="preview-heading"><div><h1>导入预览</h1><p>{{ data.preview.filename }} · {{ data.preview.rows.length }} 行 · {{ data.preview.columns.length }} 列</p></div><button class="ghost-button" type="button" @click="go('/upload')">重新选择文件</button></div>
      <div class="import-toolbar">
        <label>单词表名称 <input v-model="importForm.word_list_name" required></label>
        <label>Sheet <select v-if="data.preview.sheet_names?.length > 1" :value="data.preview.sheet_name" @change="changePreviewSheet($event.target.value)"><option v-for="sheet in data.preview.sheet_names" :key="sheet" :value="sheet">{{ sheet }}</option></select><input v-else :value="data.preview.sheet_name || 'Sheet1'" disabled></label>
        <button type="button" class="secondary-button" @click="setAllRows(true)">全选行</button><button type="button" class="secondary-button" @click="setAllRows(false)">取消行</button><button type="button" class="secondary-button" @click="setAllColumns(true)">全选列</button><button type="button" class="secondary-button" @click="setAllColumns(false)">取消列</button>
        <label>批量图片 <input type="file" accept="image/*" multiple webkitdirectory directory @change="importForm.image_files = Array.from($event.target.files || [])"></label>
        <button type="button" @click="submitImport">确认导入</button>
      </div>
      <div class="word-column-options"><label v-for="column in data.preview.columns" :key="column" class="word-column-option"><input v-model="importForm.word_columns" type="checkbox" :value="column"><span>{{ column }}</span></label></div>
      <div class="table-wrap"><table class="preview-table"><thead><tr><th>导入</th><th>Excel 行</th><th v-for="column in data.preview.columns" :key="column"><label class="check-label"><input v-model="importForm.selected_columns" type="checkbox" :value="column"><span>{{ column }}</span></label></th></tr></thead><tbody><tr v-for="row in data.preview.rows" :key="row.index"><td><input v-model="importForm.selected_rows" type="checkbox" :value="row.index"></td><td>{{ row.excel_row }}</td><td v-for="column in data.preview.columns" :key="column">{{ row.values[column] || '' }}</td></tr></tbody></table></div>
    </section>
  </template>

  <template v-else-if="route.name === 'newspaper' && data">
    <section class="panel newspaper-hero"><div><p class="newspaper-kicker">China Daily Reader</p><h1>英文小报</h1><p>精选 China Daily 英文资讯，适合日常泛读和积累新闻表达。</p></div><a class="ghost-button" :href="data.source_url" target="_blank" rel="noreferrer">China Daily</a></section>
    <section class="newspaper-layout"><article v-for="section in data.sections" :key="section.key" class="panel newspaper-section"><div class="newspaper-section-head"><h2>{{ section.name }}</h2><span>{{ section.articles?.length || 0 }} articles</span></div><p v-if="section.error" class="newspaper-error">{{ section.error }}</p><div v-else class="newspaper-list"><button v-for="(article, index) in section.articles" :key="article.link || article.title" type="button" class="newspaper-card plain-card-button" :class="{ lead: index === 0, 'has-image': article.image_url }" @click="go(`/newspaper/${section.key}/${index}`)"><div v-if="article.image_url" class="newspaper-card-image"><img :src="article.image_url" :alt="article.title" loading="lazy"></div><div class="newspaper-card-content"><div class="newspaper-card-meta"><span>{{ article.source }}</span><span v-if="article.published">{{ article.published }}</span><span v-if="article.category">{{ article.category }}</span></div><h3>{{ article.title }}</h3><p>{{ article.summary || article.excerpt }}</p><small v-if="article.author">By {{ article.author }}</small></div></button></div></article></section>
  </template>

  <template v-else-if="route.name === 'newspaperArticle' && data">
    <section class="panel newspaper-article"><div class="newspaper-article-head"><div><p class="newspaper-kicker">{{ data.section.name }} · {{ data.article.source }}</p><h1>{{ data.article.title }}</h1><div class="newspaper-card-meta"><span v-if="data.article.published">{{ data.article.published }}</span><span v-if="data.article.category">{{ data.article.category }}</span><span v-if="data.article.author">By {{ data.article.author }}</span></div></div><div class="newspaper-article-actions"><button class="ghost-button" type="button" @click="go('/newspaper')">返回英文小报</button><a v-if="data.article.link" class="ghost-button" :href="data.article.link" target="_blank" rel="noreferrer">查看原文</a></div></div><figure v-if="data.article.image_url" class="newspaper-article-image"><img :src="data.article.image_url" :alt="data.article.title"></figure><p v-if="data.article.summary" class="newspaper-article-summary">{{ data.article.summary }}</p><article class="newspaper-article-body"><p v-for="(paragraph, index) in articleText(data.article)" :key="index">{{ paragraph }}</p></article></section>
  </template>

  <template v-else-if="route.name.startsWith('booklearner') && data">
    <section class="booklearner-page">
      <section class="quote-home-panel"><div class="quote-home-head"><div><h1>好词好句</h1><p>从书籍学习记录里整理短句、难词和阅读关注点。</p></div><div class="quote-head-actions"><button class="quote-more-link" type="button" @click="go('/booklearner')">首页</button><button class="quote-more-link" type="button" @click="go('/booklearner/quotes')">更多</button><button class="quote-more-link quote-upload-link" type="button" @click="go('/booklearner/upload')">上传</button></div></div><div class="featured-quotes" :class="{ 'featured-quotes-list': route.name === 'booklearnerQuotes' }"><article v-for="item in book.featured" :key="item.id || item.quote" class="quote-card"><p>{{ item.quote || item.text || item.sentence }}</p><strong>{{ item.title || item.bookTitle || item.book }}</strong></article><div v-if="!book.featured.length" class="quote-feed-empty">还没有书摘。</div></div></section>
      <section v-if="route.name === 'booklearnerUpload'" class="book-workspace"><aside class="query-panel"><form class="form active" @submit.prevent="analyzeBookQuery"><label>书名或作者</label><div class="input-row"><input v-model="book.query" placeholder="Pride and Prejudice"><button type="submit">分析</button></div></form><form class="form active" @submit.prevent="analyzeBookText"><label>书名</label><input v-model="book.title"><label>作者</label><input v-model="book.author"><label>书籍文件</label><input type="file" accept=".txt,.epub,text/plain,application/epub+zip" @change="book.file = $event.target.files[0]"><button class="secondary-wide-button" type="button" @click="analyzeBookFile">分析文件</button><label>书籍正文</label><textarea v-model="book.text"></textarea><button class="wide-button" type="submit">分析文本</button></form><div v-if="book.notice" class="notice">{{ book.notice }}</div></aside><section class="results"><div v-if="!book.result" class="empty-state"><h2>等待分析</h2><p>搜索书名、上传 txt/epub，或粘贴正文。</p></div><div v-else class="panel"><h2>{{ book.result.book?.title || book.result.title || '分析结果' }}</h2><p>{{ book.result.book?.author || book.result.author }}</p><button type="button" @click="saveBookAnalysis">保存</button><button type="button" class="secondary-button" @click="createBookWordList">生成单词表</button><pre class="booklearner-json">{{ JSON.stringify(book.result, null, 2) }}</pre></div></section></section>
      <section v-if="route.name !== 'booklearnerUpload'" class="word-grid"><article v-for="item in book.history" :key="item.id" class="word-card list-card"><button class="list-card-link plain-card-button" type="button" @click="go(`/booklearner/detail/${item.id}`)"><div class="image-fallback">B</div><div class="word-card-body"><div class="word-card-title"><strong>{{ item.title || item.query || `记录 #${item.id}` }}</strong><span class="status">书摘</span></div><p>{{ item.createdAt || item.created_at }}</p></div></button></article></section>
      <section v-if="route.name === 'booklearnerDetail' && book.result" class="panel"><h2>{{ book.result.book?.title || book.result.title || '书籍详情' }}</h2><button type="button" class="secondary-button" @click="createBookWordList">生成单词表</button><pre class="booklearner-json">{{ JSON.stringify(book.result, null, 2) }}</pre></section>
    </section>
  </template>

  <template v-else-if="route.name === 'wrongWords' && data">
    <section class="word-grid"><article v-for="group in data.groups" :key="group.date" class="word-card list-card"><button class="list-card-link plain-card-button" type="button" @click="go(`/challenge-calendar/${group.date}`)"><div class="image-fallback">×</div><div class="word-card-body"><div class="word-card-title"><strong>{{ group.date }}</strong><span class="status failed">{{ group.count }} 词</span></div><p class="wrong-list-summary">错 {{ group.wrong_total }} 次</p></div></button></article><div v-if="!data.groups.length" class="empty-state">生词本还是空的。</div></section>
  </template>

  <template v-else-if="route.name === 'challengeDay' && data">
    <section class="challenge-day-stats"><div class="panel challenge-day-filter"><span>答对</span><strong class="stat-correct">{{ data.correct }}</strong></div><div class="panel challenge-day-filter"><span>答错</span><strong class="stat-wrong">{{ data.wrong }}</strong></div><button class="panel challenge-day-back" type="button" @click="go('/')"><span>返回</span><strong>挑战日历</strong></button></section>
    <section class="challenge-day-grid"><a v-for="item in data.words" :key="`${item.id}-${item.status}`" class="panel challenge-day-word" :class="item.status === 'correct' ? 'is-correct' : 'is-wrong'" :href="`/vue/words/${item.id}${item.word_list_id ? `?edit=1&list_id=${item.word_list_id}` : '?edit=1'}`"><span class="challenge-day-result">{{ item.status === 'correct' ? '✓' : '×' }}</span><img v-if="item.image_url" :src="item.image_url" :alt="item.word" loading="lazy"><div v-else class="image-fallback">{{ fallbackLetter(item) }}</div><div class="challenge-day-word-body"><div><h2>{{ item.word }}</h2></div><strong class="challenge-day-status" :class="item.status === 'correct' ? 'is-correct' : 'is-wrong'">{{ item.status === 'correct' ? '正确' : '错误' }}</strong><p>{{ item.chinese_definition || item.english_definition || '暂无定义' }}</p><div class="challenge-day-counts"><span>对 {{ item.correct_count }}</span><span>错 {{ item.wrong_count }}</span></div></div></a></section>
  </template>
</template>
