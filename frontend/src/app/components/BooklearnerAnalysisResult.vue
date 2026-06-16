<script setup>
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
      <p>搜索书名、上传 txt/epub，或粘贴正文。</p>
    </div>
    <div v-else class="panel">
      <h2>{{ book.result.book?.title || book.result.title || "分析结果" }}</h2>
      <p>{{ book.result.book?.author || book.result.author }}</p>
      <button type="button" @click="saveBookAnalysis">保存</button>
      <button type="button" class="secondary-button" @click="createBookWordList">生成单词表</button>
      <pre class="booklearner-json">{{ JSON.stringify(book.result, null, 2) }}</pre>
    </div>
  </section>
</template>
