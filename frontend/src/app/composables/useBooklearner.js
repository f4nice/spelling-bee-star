import { ref } from 'vue';
import { fetchJson } from '../utils.js';

export function useBooklearner({ route, go }) {
  const book = ref({ query: '', title: '', author: '', text: '', file: null, result: null, history: [], featured: [], suggestions: [], notice: '' });

  async function loadBooklearner() {
    book.value.result = null;
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

  return {
    book,
    loadBooklearner,
    analyzeBookQuery,
    analyzeBookText,
    analyzeBookFile,
    saveBookAnalysis,
    createBookWordList,
  };
}
