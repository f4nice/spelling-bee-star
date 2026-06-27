<script setup>
import BooklearnerResultPanel from "./BooklearnerResultPanel.vue";

defineProps({
  book: {
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
</script>

<template>
  <section class="results">
    <div v-if="!book.result" class="empty-state">
      <h2>等待分析</h2>
      <p>搜索书名或上传 TXT / EPUB 后，这里会展示好句和生僻词预览。</p>
    </div>
    <BooklearnerResultPanel
      v-else
      :result="book.result"
      :save-book-analysis="saveBookAnalysis"
      :create-book-word-list="createBookWordList"
    />
  </section>
</template>
