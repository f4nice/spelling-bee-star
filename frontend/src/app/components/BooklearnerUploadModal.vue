<script setup>
import BooklearnerUploadWorkspace from "./BooklearnerUploadWorkspace.vue";

defineProps({
  book: {
    type: Object,
    required: true,
  },
  analyzeBookQuery: {
    type: Function,
    required: true,
  },
  analyzeBookText: {
    type: Function,
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

defineEmits(["close"]);
</script>

<template>
  <div class="book-upload-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="bookUploadModalTitle">
    <section class="book-upload-modal">
      <header class="book-upload-modal-head">
        <div>
          <span class="eyebrow">BOOK UPLOAD</span>
          <h2 id="bookUploadModalTitle">上传书籍</h2>
        </div>
        <button class="secondary-button" type="button" @click="$emit('close')">关闭</button>
      </header>

      <BooklearnerUploadWorkspace
        :book="book"
        :analyze-book-query="analyzeBookQuery"
        :analyze-book-text="analyzeBookText"
        :analyze-book-file="analyzeBookFile"
        :save-book-analysis="saveBookAnalysis"
        :create-book-word-list="createBookWordList"
      />
    </section>
  </div>
</template>
