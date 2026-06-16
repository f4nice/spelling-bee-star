<script setup>
defineProps([
  "data",
  "go",
  "fallbackLetter"
]);
</script>

<template>
    <section class="challenge-day-stats"><div class="panel challenge-day-filter"><span>答对</span><strong class="stat-correct">{{ data.correct }}</strong></div><div class="panel challenge-day-filter"><span>答错</span><strong class="stat-wrong">{{ data.wrong }}</strong></div><button class="panel challenge-day-back" type="button" @click="go('/')"><span>返回</span><strong>挑战日历</strong></button></section>
    <section class="challenge-day-grid"><a v-for="item in data.words" :key="`${item.id}-${item.status}`" class="panel challenge-day-word" :class="item.status === 'correct' ? 'is-correct' : 'is-wrong'" :href="`/vue/words/${item.id}${item.word_list_id ? `?edit=1&list_id=${item.word_list_id}` : '?edit=1'}`"><span class="challenge-day-result">{{ item.status === 'correct' ? '✓' : '×' }}</span><img v-if="item.image_url" :src="item.image_url" :alt="item.word" loading="lazy"><div v-else class="image-fallback">{{ fallbackLetter(item) }}</div><div class="challenge-day-word-body"><div><h2>{{ item.word }}</h2></div><strong class="challenge-day-status" :class="item.status === 'correct' ? 'is-correct' : 'is-wrong'">{{ item.status === 'correct' ? '正确' : '错误' }}</strong><p>{{ item.chinese_definition || item.english_definition || '暂无定义' }}</p><div class="challenge-day-counts"><span>对 {{ item.correct_count }}</span><span>错 {{ item.wrong_count }}</span></div></div></a></section>
</template>
