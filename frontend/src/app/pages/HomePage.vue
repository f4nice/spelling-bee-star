<script setup>
import { computed } from "vue";
import HomeChallengeCalendar from "../components/HomeChallengeCalendar.vue";
import HomeFeaturedLists from "../components/HomeFeaturedLists.vue";
import HomeStatsGrid from "../components/HomeStatsGrid.vue";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
  fallbackLetter: {
    type: Function,
    required: true,
  },
});

const stats = computed(() => props.data?.stats || {});
const todayWrongWords = computed(() => stats.value.today_wrong_words || []);
const todayCorrect = computed(() => Number(stats.value.today_correct || 0));
const todayWrong = computed(() => Number(stats.value.today_wrong || 0));
const todayTotal = computed(() => Number(stats.value.today_total || 0));
const todayWrongCount = computed(() => Number(stats.value.today_wrong_count || 0));
const todayAccuracy = computed(() => (todayTotal.value ? Math.round((todayCorrect.value / todayTotal.value) * 100) : 0));

function openTodayWrongChallenge() {
  const listId = stats.value.today_wrong_list_id;
  if (!listId || todayWrongCount.value <= 0) {
    props.go("/wrong-words");
    return;
  }
  const params = new URLSearchParams({
    daily_count: String(Math.min(Math.max(todayWrongCount.value, 1), 500)),
    start_count: "0",
    wrong_date: props.data.today || "",
    restart: "1",
  });
  props.go(`/challenge/${listId}?${params.toString()}`);
}
</script>

<template>
  <section class="home-page">
    <section class="home-hero panel">
      <div class="home-hero-copy">
        <p class="section-kicker">Speakeasy</p>
        <h1>今天从这里开始</h1>
        <p>把单词表、错词复习和每日挑战放在同一个节奏里，打开首页就能继续今天的学习。</p>
        <div class="home-hero-actions">
          <button class="primary-action-button" type="button" @click="go('/lists')">继续学习</button>
          <button class="secondary-button" type="button" @click="openTodayWrongChallenge">练习错词</button>
        </div>
      </div>

      <div class="home-hero-board" aria-label="今日学习概览">
        <article class="home-today-card is-correct">
          <span>今日答对</span>
          <strong>{{ todayCorrect }}</strong>
          <small>Accuracy {{ todayAccuracy }}%</small>
        </article>
        <article class="home-today-card is-wrong">
          <span>今日答错</span>
          <strong>{{ todayWrong }}</strong>
          <small>待纠正 {{ todayWrongCount }}</small>
        </article>
        <article class="home-today-card is-total">
          <span>今日完成</span>
          <strong>{{ todayTotal }}</strong>
          <small>{{ data.today }}</small>
        </article>
      </div>
    </section>

    <HomeStatsGrid :stats="data.stats" :go="go" />

    <section class="panel home-math-card" aria-labelledby="home-math-title">
      <div class="home-math-symbol" aria-hidden="true">×</div>
      <div class="home-math-copy">
        <p class="section-kicker">DAILY MATH</p>
        <h2 id="home-math-title">趣味数学</h2>
        <p>每天 5 道三位数乘法 · 每题 10 分钟 · 答对获得 100 猫咪能量</p>
      </div>
      <button class="primary-action-button" type="button" @click="go('/fun-math')">去挑战 →</button>
    </section>

    <section v-if="todayWrongWords.length" class="panel home-wrong-panel home-wrong-strip">
      <div class="home-wrong-heading">
        <p class="section-kicker">Mistakes</p>
        <h2>今天的错词</h2>
      </div>
      <div class="home-wrong-chips" aria-label="今天的错词">
        <button
          v-for="item in todayWrongWords"
          :key="item.word.id"
          type="button"
          @click="go(`/words/${item.word.id}?edit=1`)"
        >
          <strong>{{ item.word.word }}</strong>
          <span>错 {{ item.wrong_count }}</span>
        </button>
      </div>
    </section>

    <HomeChallengeCalendar :calendar="data.calendar" :growth="data.growth" :go="go" />
    <HomeFeaturedLists :cards="data.featured_cards" :go="go" :fallback-letter="fallbackLetter" />
  </section>
</template>

<style scoped>
.home-math-card { display: flex; align-items: center; gap: 20px; padding: 24px; margin-block: 22px; background: linear-gradient(115deg, #f0faf6, #fff9e8); border-color: #c6e4d6; }
.home-math-symbol { display: grid; place-items: center; flex: 0 0 64px; height: 64px; border-radius: 20px; background: #d9f1e6; color: #146e55; font: 800 46px/1 sans-serif; transform: rotate(-7deg); }
.home-math-copy { flex: 1; min-width: 0; }
.home-math-copy h2 { margin: 4px 0 6px; }
.home-math-copy p { margin: 0; color: #526c62; line-height: 1.6; }
.home-math-card > button { flex-shrink: 0; }
@media (max-width: 600px) { .home-math-card { flex-wrap: wrap; padding: 20px; gap: 14px; } .home-math-symbol { flex-basis: 48px; height: 48px; font-size: 36px; border-radius: 15px; } .home-math-card > button { width: 100%; min-height: 44px; } }
</style>
