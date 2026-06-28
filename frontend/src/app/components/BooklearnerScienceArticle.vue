<script setup>
import { computed, ref, watch } from "vue";

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
  loadScienceFullArticle: {
    type: Function,
    required: true,
  },
});

const article = computed(() => props.book.science?.article || null);
const sources = computed(() => props.book.science?.sources || []);
const fullArticle = computed(() => (Array.isArray(article.value?.fullArticle) ? article.value.fullArticle : []));
const readingParagraphs = computed(() => (fullArticle.value.length ? fullArticle.value : article.value?.article || []));
const illustrations = computed(() => (Array.isArray(article.value?.illustrations) ? article.value.illustrations : []));
const readingBlocks = computed(() => {
  const blocks = [];
  readingParagraphs.value.forEach((paragraph, index) => {
    blocks.push({ type: "paragraph", key: `p:${index}:${paragraph}`, text: paragraph });
    if (fullArticle.value.length && index === 1 && illustrations.value[0]) {
      blocks.push({ type: "illustration", key: `i:${illustrations.value[0].imageUrl}`, item: illustrations.value[0] });
    }
  });
  return blocks;
});
const revealedAnswers = ref({});
const fullArticleLoading = ref(false);
const fullArticleError = ref("");

watch(
  () => article.value?.slug,
  () => {
    revealedAnswers.value = {};
    fullArticleError.value = "";
    fullArticleLoading.value = false;
  },
);

function backToDiscoveries() {
  props.go("/booklearner/science");
}

function answerKey(item, index) {
  return `${index}:${item.question}`;
}

function answerVisible(item, index) {
  return Boolean(revealedAnswers.value[answerKey(item, index)]);
}

function toggleAnswer(item, index) {
  const key = answerKey(item, index);
  revealedAnswers.value = {
    ...revealedAnswers.value,
    [key]: !revealedAnswers.value[key],
  };
}

async function loadFullArticle() {
  if (!article.value || fullArticleLoading.value) return;
  fullArticleLoading.value = true;
  fullArticleError.value = "";
  try {
    await props.loadScienceFullArticle(article.value.slug || props.route.params.slug);
  } catch (error) {
    fullArticleError.value = error.message || "全文生成失败，请稍后再试。";
  } finally {
    fullArticleLoading.value = false;
  }
}
</script>

<template>
  <section v-if="article" class="panel science-article-panel">
    <button type="button" class="secondary-button science-back-button" @click="backToDiscoveries">
      返回科学探索
    </button>
    <div class="science-article-kicker">
      <span class="eyebrow">EXPLORE PAGE</span>
      <strong>{{ article.topic }}</strong>
      <small>{{ article.levelLabel }}</small>
    </div>
    <h1>{{ article.title }}</h1>
    <div class="science-article-actions">
      <button
        type="button"
        class="secondary-button science-read-more-button"
        :disabled="fullArticleLoading"
        @click="loadFullArticle"
      >
        {{ fullArticleLoading ? "生成中..." : fullArticle.length ? "更新全文" : "阅读全文" }}
      </button>
    </div>
    <p v-if="fullArticleError" class="notice science-full-article-error">{{ fullArticleError }}</p>
    <p class="science-article-summary">{{ article.summary }}</p>
    <div v-if="article.imageUrl" class="science-article-hero-image">
      <img :src="article.imageUrl" :alt="article.title" loading="lazy" />
    </div>

    <div class="science-article-source">
      <span>参考来源</span>
      <a :href="article.sourceUrl" target="_blank" rel="noreferrer">{{ article.source }}</a>
    </div>

    <article class="science-reading-body" :class="{ 'has-full-article': fullArticle.length }">
      <div v-if="article.fullArticleSourceNote" class="science-full-article-note">
        {{ article.fullArticleSourceNote }}
      </div>
      <template v-for="block in readingBlocks" :key="block.key">
        <p v-if="block.type === 'paragraph'">{{ block.text }}</p>
        <figure v-else class="science-inline-figure">
          <img :src="block.item.imageUrl" :alt="block.item.title" loading="lazy" />
          <figcaption>{{ block.item.caption }}</figcaption>
        </figure>
      </template>
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
        <li v-for="(item, index) in article.quiz" :key="item.question">
          <div class="science-quiz-question-row">
            <strong>{{ item.question }}</strong>
            <button
              type="button"
              class="science-answer-toggle"
              :aria-label="answerVisible(item, index) ? '隐藏答案' : '显示答案'"
              @click="toggleAnswer(item, index)"
            >
              <span aria-hidden="true">👁</span>
            </button>
          </div>
          <span v-if="answerVisible(item, index)" class="science-quiz-answer">{{ item.answer }}</span>
          <span v-else class="science-quiz-answer is-hidden" aria-hidden="true"></span>
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
      返回科学探索
    </button>
    <p class="notice">正在加载知识点...</p>
  </section>
</template>
