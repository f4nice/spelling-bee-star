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
