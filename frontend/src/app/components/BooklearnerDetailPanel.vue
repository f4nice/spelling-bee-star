<script setup>
import { computed } from "vue";

const props = defineProps({
  route: {
    type: Object,
    required: true,
  },
  book: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
  createBookWordList: {
    type: Function,
    required: true,
  },
});

const result = computed(() => props.book.result || {});
const bookInfo = computed(() => result.value.book || {});
const title = computed(() => bookInfo.value.title || result.value.title || "书籍详情");
const author = computed(() => {
  if (Array.isArray(bookInfo.value.authors) && bookInfo.value.authors.length) return bookInfo.value.authors.join(" / ");
  return bookInfo.value.author || result.value.author || "作者未记录";
});
const coverUrl = computed(() => bookInfo.value.coverUrl || bookInfo.value.cover_url || "");
const quotes = computed(() => result.value.quotes || []);
const vocabulary = computed(() => result.value.vocabulary || result.value.words || []);
const stats = computed(() => result.value.stats || {});
const currentQuote = computed(() => {
  props.route.params.id;
  return new URLSearchParams(window.location.search).get("quote") || "";
});
const canCreateList = computed(() => vocabulary.value.length > 0);
const relatedBooks = computed(() => {
  const currentId = Number(props.route.params.id);
  const key = author.value && author.value !== "作者未记录" ? author.value : "";
  return (props.book.history || [])
    .filter((item) => Number(item.id) !== currentId)
    .filter((item) => !key || item.authors_text === key)
    .slice(0, 4);
});

function quoteText(item) {
  return item.text || item.quote || item.sentence || "";
}

function openRelated(item) {
  props.go(`/booklearner/detail/${item.id}`);
}
</script>

<template>
  <section v-if="book.result" class="book-detail-layout">
    <article class="panel book-detail-main">
      <div class="book-detail-hero">
        <div class="book-detail-cover">
          <img v-if="coverUrl" :src="coverUrl" :alt="title">
          <div v-else class="book-history-cover-fallback cover-seed-0">
            <span>书摘</span>
            <strong>{{ title.slice(0, 1).toUpperCase() }}</strong>
          </div>
        </div>
        <div class="book-detail-info">
          <span class="eyebrow">BOOK DETAIL</span>
          <h2>{{ title }}</h2>
          <p>{{ author }}</p>
          <div class="book-detail-stats">
            <span>好句 {{ quotes.length }} 条</span>
            <span>难词 {{ vocabulary.length }} 个</span>
            <span v-if="stats.words">原文词数 {{ stats.words }}</span>
            <span v-if="stats.sentences">句子 {{ stats.sentences }}</span>
          </div>
          <button
            type="button"
            class="wide-button book-detail-create-button"
            :disabled="!canCreateList"
            @click="createBookWordList"
          >
            生成单词表
          </button>
          <p v-if="book.notice" class="notice">{{ book.notice }}</p>
        </div>
      </div>

      <section v-if="relatedBooks.length" class="book-related-section">
        <div class="book-section-head">
          <span class="eyebrow">RELATED BOOKS</span>
          <h3>作者相关书籍</h3>
        </div>
        <div class="book-related-list">
          <button
            v-for="item in relatedBooks"
            :key="item.id"
            type="button"
            class="book-related-card"
            @click="openRelated(item)"
          >
            <img v-if="item.coverUrl" :src="item.coverUrl" :alt="item.title || item.query_text">
            <span v-else>{{ (item.title || item.query_text || '书').slice(0, 1).toUpperCase() }}</span>
            <strong>{{ item.title || item.query_text }}</strong>
          </button>
        </div>
      </section>

      <section class="book-quotes-section">
        <div class="book-section-head">
          <span class="eyebrow">QUOTES</span>
          <h3>这本书的其他好句</h3>
        </div>
        <div class="book-detail-quote-list">
          <article
            v-for="(item, index) in quotes"
            :key="`${index}-${quoteText(item)}`"
            class="book-detail-quote"
            :class="{ 'is-current': currentQuote && quoteText(item) === currentQuote }"
          >
            <span>{{ String(index + 1).padStart(2, "0") }}</span>
            <p>{{ quoteText(item) }}</p>
            <small v-if="item.note">{{ item.note }}</small>
          </article>
        </div>
      </section>
    </article>

    <aside class="panel book-vocabulary-panel">
      <div class="book-section-head">
        <span class="eyebrow">VOCABULARY</span>
        <h3>难点单词</h3>
      </div>
      <div class="book-vocabulary-list">
        <article v-for="item in vocabulary" :key="item.word" class="book-vocabulary-card">
          <strong>{{ item.word }}</strong>
          <span v-if="item.partOfSpeech">{{ item.partOfSpeech }}</span>
          <p>{{ item.definition }}</p>
          <small v-if="item.example">{{ item.example }}</small>
        </article>
        <p v-if="!vocabulary.length" class="notice">这本书还没有难词记录。</p>
      </div>
    </aside>
  </section>
</template>
