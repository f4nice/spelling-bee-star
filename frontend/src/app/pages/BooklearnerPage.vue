<script setup>
defineProps([
  "route",
  "book",
  "go",
  "analyzeBookQuery",
  "analyzeBookText",
  "analyzeBookFile",
  "saveBookAnalysis",
  "createBookWordList"
]);
</script>

<template>
    <section class="booklearner-page">
      <section class="quote-home-panel"><div class="quote-home-head"><div><h1>好词好句</h1><p>从书籍学习记录里整理短句、难词和阅读关注点。</p></div><div class="quote-head-actions"><button class="quote-more-link" type="button" @click="go('/booklearner')">首页</button><button class="quote-more-link" type="button" @click="go('/booklearner/quotes')">更多</button><button class="quote-more-link quote-upload-link" type="button" @click="go('/booklearner/upload')">上传</button></div></div><div class="featured-quotes" :class="{ 'featured-quotes-list': route.name === 'booklearnerQuotes' }"><article v-for="item in book.featured" :key="item.id || item.quote" class="quote-card"><p>{{ item.quote || item.text || item.sentence }}</p><strong>{{ item.title || item.bookTitle || item.book }}</strong></article><div v-if="!book.featured.length" class="quote-feed-empty">还没有书摘。</div></div></section>
      <section v-if="route.name === 'booklearnerUpload'" class="book-workspace"><aside class="query-panel"><form class="form active" @submit.prevent="analyzeBookQuery"><label>书名或作者</label><div class="input-row"><input v-model="book.query" placeholder="Pride and Prejudice"><button type="submit">分析</button></div></form><form class="form active" @submit.prevent="analyzeBookText"><label>书名</label><input v-model="book.title"><label>作者</label><input v-model="book.author"><label>书籍文件</label><input type="file" accept=".txt,.epub,text/plain,application/epub+zip" @change="book.file = $event.target.files[0]"><button class="secondary-wide-button" type="button" @click="analyzeBookFile">分析文件</button><label>书籍正文</label><textarea v-model="book.text"></textarea><button class="wide-button" type="submit">分析文本</button></form><div v-if="book.notice" class="notice">{{ book.notice }}</div></aside><section class="results"><div v-if="!book.result" class="empty-state"><h2>等待分析</h2><p>搜索书名、上传 txt/epub，或粘贴正文。</p></div><div v-else class="panel"><h2>{{ book.result.book?.title || book.result.title || '分析结果' }}</h2><p>{{ book.result.book?.author || book.result.author }}</p><button type="button" @click="saveBookAnalysis">保存</button><button type="button" class="secondary-button" @click="createBookWordList">生成单词表</button><pre class="booklearner-json">{{ JSON.stringify(book.result, null, 2) }}</pre></div></section></section>
      <section v-if="route.name !== 'booklearnerUpload'" class="word-grid"><article v-for="item in book.history" :key="item.id" class="word-card list-card"><button class="list-card-link plain-card-button" type="button" @click="go(`/booklearner/detail/${item.id}`)"><div class="image-fallback">B</div><div class="word-card-body"><div class="word-card-title"><strong>{{ item.title || item.query || `记录 #${item.id}` }}</strong><span class="status">书摘</span></div><p>{{ item.createdAt || item.created_at }}</p></div></button></article></section>
      <section v-if="route.name === 'booklearnerDetail' && book.result" class="panel"><h2>{{ book.result.book?.title || book.result.title || '书籍详情' }}</h2><button type="button" class="secondary-button" @click="createBookWordList">生成单词表</button><pre class="booklearner-json">{{ JSON.stringify(book.result, null, 2) }}</pre></section>
    </section>
</template>
