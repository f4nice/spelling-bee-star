<script setup>
import { computed } from "vue";

const props = defineProps({
  book: {
    type: Object,
    required: true,
  },
  createBookWordList: {
    type: Function,
    required: true,
  },
});

const result = computed(() => props.book.result || {});
const bookInfo = computed(() => result.value.book || {});
const title = computed(() => bookInfo.value.title || result.value.title || "书摘详情");
const vocabulary = computed(() => result.value.vocabulary || result.value.words || []);
const stats = computed(() => result.value.stats || {});
const canCreateList = computed(() => vocabulary.value.length > 0);
</script>

<template>
  <section v-if="book.result" class="panel book-detail-panel">
    <div class="book-detail-summary">
      <div>
        <span class="eyebrow">BOOK DETAIL</span>
        <h2>{{ title }}</h2>
        <p v-if="bookInfo.authors?.length">{{ bookInfo.authors.join(" / ") }}</p>
        <p v-else-if="bookInfo.author">{{ bookInfo.author }}</p>
      </div>
      <button
        type="button"
        class="wide-button book-detail-create-button"
        :disabled="!canCreateList"
        @click="createBookWordList"
      >
        生成单词表
      </button>
    </div>

    <div class="book-detail-stats">
      <span>单词 {{ vocabulary.length }} 个</span>
      <span v-if="stats.words">原文词数 {{ stats.words }}</span>
      <span v-if="stats.sentences">句子 {{ stats.sentences }}</span>
    </div>

    <p v-if="!canCreateList" class="notice">这条书摘还没有可生成的单词，请重新上传或分析书籍。</p>
    <p v-if="book.notice" class="notice">{{ book.notice }}</p>
  </section>
</template>
