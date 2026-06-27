<script setup>
import { computed } from "vue";

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
  loadScienceArticle: {
    type: Function,
    required: true,
  },
});

const article = computed(() => props.book.science?.article || null);
const sources = computed(() => props.book.science?.sources || []);

function backToDiscoveries() {
  props.go("/booklearner");
}
</script>

<template>
  <section v-if="article" class="panel science-article-panel">
    <button type="button" class="secondary-button science-back-button" @click="backToDiscoveries">
      返回好词好句
    </button>
    <div class="science-article-kicker">
      <span class="eyebrow">EXPLORE PAGE</span>
      <strong>{{ article.topic }}</strong>
      <small>{{ article.levelLabel }}</small>
    </div>
    <h1>{{ article.title }}</h1>
    <p class="science-article-summary">{{ article.summary }}</p>

    <div class="science-article-source">
      <span>参考来源</span>
      <a :href="article.sourceUrl" target="_blank" rel="noreferrer">{{ article.source }}</a>
    </div>

    <article class="science-reading-body">
      <p v-for="paragraph in article.article" :key="paragraph">{{ paragraph }}</p>
    </article>

    <section class="science-article-section">
      <div class="book-section-head">
        <span class="eyebrow">WORDS I LEARNED</span>
        <h3>科学词汇</h3>
      </div>
      <div class="science-vocabulary-grid">
        <span v-for="item in article.words" :key="item.word">{{ item.word }}</span>
      </div>
    </section>

    <section class="science-article-section">
      <div class="book-section-head">
        <span class="eyebrow">MINI QUIZ</span>
        <h3>3 道小题</h3>
      </div>
      <ol class="science-quiz-list">
        <li v-for="item in article.quiz" :key="item.question">
          <strong>{{ item.question }}</strong>
          <span>{{ item.answer }}</span>
        </li>
      </ol>
    </section>

    <section class="science-parent-note">
      <span class="eyebrow">PARENT NOTES</span>
      <p>{{ article.parentNote }}</p>
    </section>

    <div class="science-source-strip">
      <span>来源池</span>
      <a v-for="item in sources" :key="item.name" :href="item.url" target="_blank" rel="noreferrer">
        {{ item.name }}
      </a>
    </div>
  </section>

  <section v-else class="panel science-article-panel">
    <button type="button" class="secondary-button science-back-button" @click="backToDiscoveries">
      返回好词好句
    </button>
    <p class="notice">正在加载知识点...</p>
  </section>
</template>
