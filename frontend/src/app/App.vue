<script setup>
import { computed, onMounted, ref } from 'vue';
import ChallengeApp from '../challenge/ChallengeApp.vue';

const route = ref(parseRoute());
const data = ref(null);
const loading = ref(false);
const error = ref('');

window.addEventListener('popstate', () => {
  route.value = parseRoute();
  loadRoute();
});

const routeTitle = computed(() => {
  if (route.value.name === 'lists') return '我的单词表';
  if (route.value.name === 'listDetail') return data.value?.word_list?.name || '单词表';
  if (route.value.name === 'wrongWords') return '我的生词本';
  if (route.value.name === 'challengeDay') return `${route.value.params.day} 挑战词汇`;
  if (route.value.name === 'challenge') return 'Vue 挑战';
  return '今天从这里开始';
});

function parseRoute() {
  const path = window.location.pathname.replace(/^\/vue\/?/, '').replace(/\/$/, '');
  const parts = path ? path.split('/') : [];
  if (!parts.length) return { name: 'home', params: {} };
  if (parts[0] === 'lists' && parts[1]) return { name: 'listDetail', params: { id: Number(parts[1]) } };
  if (parts[0] === 'lists') return { name: 'lists', params: {} };
  if (parts[0] === 'wrong-words') return { name: 'wrongWords', params: {} };
  if (parts[0] === 'challenge-calendar' && parts[1]) return { name: 'challengeDay', params: { day: parts[1] } };
  if (parts[0] === 'challenge' && parts[1]) return { name: 'challenge', params: { id: Number(parts[1]) } };
  return { name: 'home', params: {} };
}

function go(path) {
  history.pushState(null, '', `/vue${path}`);
  route.value = parseRoute();
  loadRoute();
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error('页面数据加载失败');
  return response.json();
}

async function loadRoute() {
  if (route.value.name === 'challenge') {
    data.value = null;
    error.value = '';
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    if (route.value.name === 'home') data.value = await fetchJson('/api/vue/home');
    if (route.value.name === 'lists') data.value = await fetchJson('/api/vue/lists');
    if (route.value.name === 'listDetail') data.value = await fetchJson(`/api/vue/lists/${route.value.params.id}`);
    if (route.value.name === 'wrongWords') data.value = await fetchJson('/api/vue/wrong-words');
    if (route.value.name === 'challengeDay') data.value = await fetchJson(`/api/vue/challenge-calendar/${route.value.params.day}`);
  } catch (err) {
    error.value = err.message || '页面数据加载失败';
  } finally {
    loading.value = false;
  }
}

function imageForWord(word) {
  return word?.image_url || '';
}

function fallbackLetter(word) {
  return (word?.word || '?').slice(0, 1).toUpperCase();
}

onMounted(loadRoute);
</script>

<template>
  <section class="panel vue-page-heading">
    <div>
      <p class="section-kicker">Vue App</p>
      <h1>{{ routeTitle }}</h1>
    </div>
    <nav class="vue-page-nav" aria-label="Vue 页面导航">
      <button type="button" class="secondary-button" @click="go('/')">首页</button>
      <button type="button" class="secondary-button" @click="go('/lists')">我的单词表</button>
      <button type="button" class="secondary-button" @click="go('/wrong-words')">我的生词本</button>
      <a class="ghost-button" href="/">返回旧版</a>
    </nav>
  </section>

  <div v-if="loading" class="empty-state">正在加载...</div>
  <div v-else-if="error" class="error-box">{{ error }}</div>

  <template v-else-if="route.name === 'challenge'">
    <div id="challenge-vue-app" :data-word-list-id="route.params.id">
      <ChallengeApp />
    </div>
  </template>

  <template v-else-if="route.name === 'home' && data">
    <section class="home-stats-grid">
      <button class="home-stat-card panel" type="button" @click="go('/lists')">
        <span>我的单词表</span><strong>{{ data.stats.word_lists }}</strong><small>{{ data.stats.words }} 个单词</small>
      </button>
      <a class="home-stat-card panel" href="/newspaper"><span>英文小报</span><strong>Today</strong><small>China Daily 今日泛读</small></a>
      <a class="home-stat-card panel" href="/booklearner"><span>好词好句</span><strong>Books</strong><small>书摘与难点词</small></a>
      <button class="home-stat-card panel" type="button" @click="go('/wrong-words')">
        <span>我的生词本</span><strong>{{ data.stats.wrong_words }}</strong><small>今日 {{ data.stats.today_wrong_count }} 个</small>
      </button>
    </section>

    <section class="panel calendar-panel home-calendar">
      <div class="calendar-heading">
        <div>
          <p class="section-kicker">Challenge</p>
          <h2>挑战日历</h2>
          <p>{{ data.calendar.title }} · 本月答对 {{ data.calendar.month_correct }} 个，答错 {{ data.calendar.month_wrong }} 个</p>
        </div>
      </div>
      <div class="challenge-calendar">
        <div v-for="weekday in data.calendar.weekdays" :key="weekday" class="calendar-weekday">{{ weekday }}</div>
        <template v-for="(week, weekIndex) in data.calendar.weeks" :key="weekIndex">
          <button
            v-for="(day, dayIndex) in week"
            :key="`${weekIndex}-${dayIndex}`"
            type="button"
            class="calendar-day"
            :class="{ today: day.is_today, empty: !day.day, 'has-records': day.total }"
            :disabled="!day.total"
            @click="day.total && go(`/challenge-calendar/${day.date}`)"
          >
            <span v-if="day.day" class="calendar-day-number">{{ day.day }}</span>
            <span v-if="day.total" class="calendar-total">{{ day.total }} 个</span>
          </button>
        </template>
      </div>
    </section>

    <section class="home-section-head">
      <div><p class="section-kicker">Lists</p><h2>我的单词表</h2></div>
      <button class="ghost-button" type="button" @click="go('/lists')">全部单词表</button>
    </section>
    <section class="word-grid home-list-grid">
      <article v-for="card in data.featured_cards" :key="card.list.id" class="word-card list-card">
        <button class="list-card-link plain-card-button" type="button" @click="go(`/lists/${card.list.id}`)">
          <img v-if="card.cover_word?.image_url" :src="card.cover_word.image_url" :alt="card.list.name">
          <div v-else class="image-fallback">{{ fallbackLetter(card.cover_word) }}</div>
          <div class="word-card-body"><div class="word-card-title"><strong>{{ card.list.name }}</strong><span class="status">{{ card.count }} 词</span></div></div>
        </button>
      </article>
    </section>
  </template>

  <template v-else-if="route.name === 'lists' && data">
    <section class="word-grid">
      <article v-for="card in data.cards" :key="card.list.id" class="word-card list-card">
        <button class="list-card-link plain-card-button" type="button" @click="go(`/lists/${card.list.id}`)">
          <img v-if="card.cover_word?.image_url" :src="card.cover_word.image_url" :alt="card.list.name">
          <div v-else class="image-fallback">{{ fallbackLetter(card.cover_word) }}</div>
          <div class="word-card-body"><div class="word-card-title"><strong>{{ card.list.name }}</strong><span class="status">{{ card.count }} 词</span></div></div>
        </button>
        <div class="challenge-card-actions">
          <div class="mini-progress"><span>{{ card.challenge.completed }} / {{ card.challenge.total }}</span><div><i :style="{ width: `${card.challenge.percent}%` }"></i></div></div>
          <button class="challenge-button" type="button" @click="go(`/challenge/${card.list.id}?daily_count=20&start_count=${card.challenge.completed}`)">Vue挑战</button>
        </div>
      </article>
    </section>
  </template>

  <template v-else-if="route.name === 'listDetail' && data">
    <section class="panel upload-panel">
      <div><h1>{{ data.word_list.name }}</h1><p>{{ data.words.length }} 个单词</p></div>
      <button class="challenge-button" type="button" @click="go(`/challenge/${data.word_list.id}?daily_count=20&start_count=${data.challenge.completed}`)">Vue挑战</button>
    </section>
    <section class="word-grid">
      <a v-for="(word, index) in data.words" :key="word.id" class="word-card" :href="word.detail_url">
        <span class="word-index-badge">#{{ index + 1 }}</span>
        <img v-if="imageForWord(word)" :src="word.image_url" :alt="word.word">
        <div v-else class="image-fallback">{{ fallbackLetter(word) }}</div>
        <div class="word-card-body">
          <div class="word-card-title">
            <strong>{{ word.word }}</strong>
            <span class="challenge-result-badges"><span class="challenge-result-badge is-correct">对 {{ word.challenge_stats.correct }}</span><span class="challenge-result-badge is-wrong">错 {{ word.challenge_stats.wrong }}</span></span>
          </div>
          <p>{{ word.chinese_definition || word.english_definition || '等待补全' }}</p>
        </div>
      </a>
    </section>
  </template>

  <template v-else-if="route.name === 'wrongWords' && data">
    <section class="word-grid">
      <article v-for="group in data.groups" :key="group.date" class="word-card list-card">
        <button class="list-card-link plain-card-button" type="button" @click="go(`/challenge-calendar/${group.date}`)">
          <div class="image-fallback">×</div>
          <div class="word-card-body"><div class="word-card-title"><strong>{{ group.date }}</strong><span class="status failed">{{ group.count }} 词</span></div><p class="wrong-list-summary">错 {{ group.wrong_total }} 次</p></div>
        </button>
      </article>
      <div v-if="!data.groups.length" class="empty-state">生词本还是空的。</div>
    </section>
  </template>

  <template v-else-if="route.name === 'challengeDay' && data">
    <section class="challenge-day-stats">
      <div class="panel challenge-day-filter"><span>答对</span><strong class="stat-correct">{{ data.correct }}</strong></div>
      <div class="panel challenge-day-filter"><span>答错</span><strong class="stat-wrong">{{ data.wrong }}</strong></div>
      <button class="panel challenge-day-back" type="button" @click="go('/')"><span>返回</span><strong>挑战日历</strong></button>
    </section>
    <section class="challenge-day-grid">
      <a v-for="item in data.words" :key="`${item.id}-${item.status}`" class="panel challenge-day-word" :class="item.status === 'correct' ? 'is-correct' : 'is-wrong'" :href="`/words/${item.id}${item.word_list_id ? `?edit=1&list_id=${item.word_list_id}` : ''}`">
        <span class="challenge-day-result">{{ item.status === 'correct' ? '✓' : '×' }}</span>
        <img v-if="item.image_url" :src="item.image_url" :alt="item.word" loading="lazy">
        <div v-else class="image-fallback">{{ fallbackLetter(item) }}</div>
        <div class="challenge-day-word-body">
          <div><h2>{{ item.word }}</h2></div>
          <strong class="challenge-day-status" :class="item.status === 'correct' ? 'is-correct' : 'is-wrong'">{{ item.status === 'correct' ? '正确' : '错误' }}</strong>
          <p>{{ item.chinese_definition || item.english_definition || '暂无定义' }}</p>
          <div class="challenge-day-counts"><span>对 {{ item.correct_count }}</span><span>错 {{ item.wrong_count }}</span></div>
        </div>
      </a>
    </section>
  </template>
</template>
