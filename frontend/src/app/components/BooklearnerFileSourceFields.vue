<script setup>
import { computed } from "vue";

const props = defineProps({
  book: {
    type: Object,
    required: true,
  },
  analyzeBookFile: {
    type: Function,
    required: true,
  },
  saveBookAnalysis: {
    type: Function,
    required: true,
  },
  createBookWordList: {
    type: Function,
    required: true,
  },
});

const result = computed(() => props.book.result || null);
const bookInfo = computed(() => result.value?.book || {});
const title = computed(() => bookInfo.value.title || result.value?.title || props.book.title || "待保存书籍");
const authors = computed(() => {
  if (Array.isArray(bookInfo.value.authors) && bookInfo.value.authors.length) return bookInfo.value.authors.join(" / ");
  return bookInfo.value.author || result.value?.author || props.book.author || "作者未记录";
});
const coverUrl = computed(() => bookInfo.value.coverUrl || bookInfo.value.cover_url || "");
const stats = computed(() => result.value?.stats || {});
const quotesCount = computed(() => (Array.isArray(result.value?.quotes) ? result.value.quotes.length : 0));
const vocabularyCount = computed(() => {
  const vocabulary = result.value?.vocabulary || result.value?.words || [];
  return Array.isArray(vocabulary) ? vocabulary.length : 0;
});
const canSaveResult = computed(() => Boolean(result.value));
const canCreateList = computed(() => vocabularyCount.value > 0);
</script>

<template>
  <label>书名</label>
  <input v-model="book.title" placeholder="可选，默认使用文件名">
  <label>作者</label>
  <input v-model="book.author" placeholder="可选">
  <label>书籍文件</label>
  <label class="book-file-picker">
    <input
      type="file"
      accept=".txt,.epub,text/plain,application/epub+zip"
      @change="book.file = $event.target.files[0]"
    >
    <span>选择 TXT / EPUB</span>
    <small>{{ book.file?.name || "未选择文件" }}</small>
  </label>
  <button class="secondary-wide-button" type="button" @click="analyzeBookFile">分析文件</button>
  <article v-if="result" class="book-upload-book-card">
    <div class="book-upload-cover">
      <img v-if="coverUrl" :src="coverUrl" :alt="title">
      <div v-else class="book-history-cover-fallback cover-seed-1">
        <span>书摘</span>
        <strong>{{ title.slice(0, 1).toUpperCase() }}</strong>
      </div>
    </div>
    <div class="book-upload-book-meta">
      <span class="eyebrow">ANALYSIS READY</span>
      <h3>{{ title }}</h3>
      <p>{{ authors }}</p>
      <div class="book-detail-stats">
        <span>好句 {{ quotesCount }} 条</span>
        <span>难词 {{ vocabularyCount }} 个</span>
        <span v-if="stats.words">词数 {{ stats.words }}</span>
        <span v-if="stats.sentences">句子 {{ stats.sentences }}</span>
      </div>
      <div class="book-upload-card-actions">
        <button type="button" class="wide-button" :disabled="!canSaveResult" @click="saveBookAnalysis">保存</button>
        <button
          type="button"
          class="secondary-wide-button"
          :disabled="!canCreateList"
          @click="createBookWordList"
        >
          生成单词表
        </button>
      </div>
    </div>
  </article>
</template>
