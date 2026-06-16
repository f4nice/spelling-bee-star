<script setup>
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
</script>

<template>
  <section class="book-workspace">
    <aside class="query-panel">
      <form class="form active" @submit.prevent="analyzeBookQuery">
        <label>书名或作者</label>
        <div class="input-row">
          <input v-model="book.query" placeholder="Pride and Prejudice">
          <button type="submit">分析</button>
        </div>
      </form>

      <form class="form active" @submit.prevent="analyzeBookText">
        <label>书名</label>
        <input v-model="book.title">
        <label>作者</label>
        <input v-model="book.author">
        <label>书籍文件</label>
        <input type="file" accept=".txt,.epub,text/plain,application/epub+zip" @change="book.file = $event.target.files[0]">
        <button class="secondary-wide-button" type="button" @click="analyzeBookFile">分析文件</button>
        <label>书籍正文</label>
        <textarea v-model="book.text"></textarea>
        <button class="wide-button" type="submit">分析文本</button>
      </form>

      <div v-if="book.notice" class="notice">{{ book.notice }}</div>
    </aside>

    <section class="results">
      <div v-if="!book.result" class="empty-state">
        <h2>等待分析</h2>
        <p>搜索书名、上传 txt/epub，或粘贴正文。</p>
      </div>
      <div v-else class="panel">
        <h2>{{ book.result.book?.title || book.result.title || '分析结果' }}</h2>
        <p>{{ book.result.book?.author || book.result.author }}</p>
        <button type="button" @click="saveBookAnalysis">保存</button>
        <button type="button" class="secondary-button" @click="createBookWordList">生成单词表</button>
        <pre class="booklearner-json">{{ JSON.stringify(book.result, null, 2) }}</pre>
      </div>
    </section>
  </section>
</template>
