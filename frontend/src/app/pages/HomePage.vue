<script setup>
defineProps([
  "data",
  "go",
  "fallbackLetter"
]);
</script>

<template>
    <section class="home-stats-grid">
      <button class="home-stat-card panel" type="button" @click="go('/lists')"><span>我的单词表</span><strong>{{ data.stats.word_lists }}</strong><small>{{ data.stats.words }} 个单词</small></button>
      <button class="home-stat-card panel" type="button" @click="go('/newspaper')"><span>英文小报</span><strong>Today</strong><small>China Daily 今日泛读</small></button>
      <button class="home-stat-card panel" type="button" @click="go('/booklearner')"><span>好词好句</span><strong>Books</strong><small>书摘与难点词</small></button>
      <button class="home-stat-card panel" type="button" @click="go('/wrong-words')"><span>我的生词本</span><strong>{{ data.stats.wrong_words }}</strong><small>今日 {{ data.stats.today_wrong_count }} 个</small></button>
    </section>
    <section class="panel calendar-panel home-calendar">
      <div class="calendar-heading"><div><p class="section-kicker">Challenge</p><h2>挑战日历</h2><p>{{ data.calendar.title }} · 本月答对 {{ data.calendar.month_correct }} 个，答错 {{ data.calendar.month_wrong }} 个</p></div></div>
      <div class="challenge-calendar">
        <div v-for="weekday in data.calendar.weekdays" :key="weekday" class="calendar-weekday">{{ weekday }}</div>
        <template v-for="(week, weekIndex) in data.calendar.weeks" :key="weekIndex">
          <button v-for="(day, dayIndex) in week" :key="`${weekIndex}-${dayIndex}`" type="button" class="calendar-day" :class="{ today: day.is_today, empty: !day.day, 'has-records': day.total }" :disabled="!day.total" @click="day.total && go(`/challenge-calendar/${day.date}`)">
            <span v-if="day.day" class="calendar-day-number">{{ day.day }}</span><span v-if="day.total" class="calendar-total">{{ day.total }} 个</span>
          </button>
        </template>
      </div>
    </section>
    <section class="home-section-head"><div><p class="section-kicker">Lists</p><h2>我的单词表</h2></div><button class="ghost-button" type="button" @click="go('/lists')">全部单词表</button></section>
    <section class="word-grid home-list-grid">
      <article v-for="card in data.featured_cards" :key="card.list.id" class="word-card list-card">
        <button class="list-card-link plain-card-button" type="button" @click="go(`/lists/${card.list.id}`)">
          <img v-if="card.cover_word?.image_url" :src="card.cover_word.image_url" :alt="card.list.name"><div v-else class="image-fallback">{{ fallbackLetter(card.cover_word) }}</div>
          <div class="word-card-body"><div class="word-card-title"><strong>{{ card.list.name }}</strong><span class="status">{{ card.count }} 词</span></div></div>
        </button>
      </article>
    </section>
</template>
