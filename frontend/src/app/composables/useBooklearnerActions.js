import { fetchJson } from '../utils.js';

export function useBooklearnerActions({ book, go }) {
  function setNotice(message) {
    book.value.notice = message;
  }

  async function analyzeBookQuery() {
    setNotice('正在分析...');
    book.value.result = await fetchJson(`/booklearner/api/analyze?q=${encodeURIComponent(book.value.query)}`);
    setNotice('分析完成');
  }

  async function analyzeBookText() {
    setNotice('正在分析文本...');
    book.value.result = await fetchJson('/booklearner/api/analyze-text', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ title: book.value.title, author: book.value.author, text: book.value.text }),
    });
    setNotice('分析完成');
  }

  async function analyzeBookFile() {
    if (!book.value.file) return;
    const form = new FormData();
    form.append('title', book.value.title);
    form.append('author', book.value.author);
    form.append('file', book.value.file);
    setNotice('正在分析文件...');
    book.value.result = await fetchJson('/booklearner/api/analyze-file', { method: 'POST', body: form });
    setNotice('分析完成');
  }

  async function saveBookAnalysis() {
    const result = await fetchJson('/booklearner/api/save-analysis', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query: book.value.query || book.value.title, result: book.value.result }),
    });
    setNotice(`已保存 #${result.storage?.id || ''}`);
  }

  async function createBookWordList() {
    const vocabulary = book.value.result?.vocabulary || book.value.result?.words || [];
    const title = book.value.result?.book?.title || book.value.title || 'BookLearner 单词表';
    const result = await fetchJson('/booklearner/api/word-list', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ title, vocabulary }),
    });
    go(`/lists/${result.word_list_id}`);
  }

  return {
    analyzeBookQuery,
    analyzeBookText,
    analyzeBookFile,
    saveBookAnalysis,
    createBookWordList,
  };
}
