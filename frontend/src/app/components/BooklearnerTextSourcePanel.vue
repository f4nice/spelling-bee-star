<script setup>
import BooklearnerFileSourceFields from "./BooklearnerFileSourceFields.vue";

defineProps({
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
</script>

<template>
  <div class="form active" role="group" aria-label="上传书籍文件">
    <BooklearnerFileSourceFields
      :book="book"
      :analyze-book-file="analyzeBookFile"
      :save-book-analysis="saveBookAnalysis"
      :create-book-word-list="createBookWordList"
    />
  </div>
</template>
