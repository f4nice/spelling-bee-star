<script setup>
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
});

function quoteText(item) {
  return item.quote || item.text || item.sentence || "";
}

function bookTitle(item) {
  return item.title || item.bookTitle || item.book || "未知书籍";
}

function authorText(item) {
  return item.author || item.authors_text || "作者未记录";
}

function openQuote(item) {
  const analysisId = item.analysisId || item.analysis_id || item.id;
  if (!analysisId) return;
  const params = new URLSearchParams();
  const quote = quoteText(item);
  if (quote) params.set("quote", quote);
  props.go(`/booklearner/detail/${analysisId}${params.toString() ? `?${params.toString()}` : ""}`);
}
</script>

<template>
  <section class="book-quote-feed panel">
    <div class="book-quote-feed-head">
      <div>
        <span class="eyebrow">QUOTE FEED</span>
        <h2>{{ route.name === "booklearnerQuotes" ? "全部好句" : "最近好句" }}</h2>
      </div>
      <button
        v-if="route.name !== 'booklearnerQuotes'"
        class="secondary-button"
        type="button"
        @click="go('/booklearner/quotes')"
      >
        查看更多
      </button>
    </div>

    <div class="book-quote-list">
      <button
        v-for="item in book.featured"
        :key="`${item.analysisId || item.id}-${quoteText(item)}`"
        class="book-quote-row"
        type="button"
        @click="openQuote(item)"
      >
        <span class="book-quote-mark">“</span>
        <span class="book-quote-text">{{ quoteText(item) }}</span>
        <span class="book-quote-source">
          {{ bookTitle(item) }}
          <span>{{ authorText(item) }}</span>
        </span>
      </button>
      <div v-if="!book.featured.length" class="quote-feed-empty">还没有书摘。</div>
    </div>
  </section>
</template>
