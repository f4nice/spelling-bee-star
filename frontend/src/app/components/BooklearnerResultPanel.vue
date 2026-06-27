<script setup>
import { computed } from "vue";

const props = defineProps({
  result: {
    type: Object,
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

const quotes = computed(() => (Array.isArray(props.result.quotes) ? props.result.quotes.slice(0, 6) : []));
const vocabulary = computed(() => {
  const items = props.result.vocabulary || props.result.words || [];
  return Array.isArray(items) ? items.slice(0, 8) : [];
});
const title = computed(() => props.result.book?.title || props.result.title || "分析结果");

function quoteText(item) {
  return item?.text || item?.quote || item?.sentence || "";
}
</script>

<template>
  <div class="panel book-upload-preview-panel">
    <section class="book-upload-preview-section is-quotes">
      <div class="book-section-head">
        <span class="eyebrow">{{ title }}</span>
        <h2>好词</h2>
      </div>
      <div class="book-upload-quote-list">
        <article v-for="(item, index) in quotes" :key="`${index}-${quoteText(item)}`" class="book-upload-quote">
          <span>{{ String(index + 1).padStart(2, "0") }}</span>
          <p>{{ quoteText(item) }}</p>
          <small v-if="item.note">{{ item.note }}</small>
        </article>
        <p v-if="!quotes.length" class="notice">还没有提取到好句。</p>
      </div>
    </section>

    <section class="book-upload-preview-section is-vocabulary">
      <div class="book-section-head">
        <span class="eyebrow">VOCABULARY</span>
        <h2>生僻词</h2>
      </div>
      <div class="book-upload-vocabulary-list">
        <article v-for="item in vocabulary" :key="item.word" class="book-vocabulary-card">
          <strong>{{ item.word }}</strong>
          <span v-if="item.partOfSpeech">{{ item.partOfSpeech }}</span>
          <p>{{ item.definition }}</p>
          <small v-if="item.example">{{ item.example }}</small>
        </article>
        <p v-if="!vocabulary.length" class="notice">还没有提取到生僻词。</p>
      </div>
    </section>
  </div>
</template>
