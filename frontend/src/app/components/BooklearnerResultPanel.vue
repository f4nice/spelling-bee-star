<script setup>
import BooklearnerJsonPreview from "./BooklearnerJsonPreview.vue";

defineProps({
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
</script>

<template>
  <div class="panel">
    <h2>{{ result.book?.title || result.title || "分析结果" }}</h2>
    <p>{{ result.book?.author || result.author }}</p>
    <button type="button" @click="saveBookAnalysis">保存</button>
    <button type="button" class="secondary-button" @click="createBookWordList">生成单词表</button>
    <BooklearnerJsonPreview :value="result" />
  </div>
</template>
