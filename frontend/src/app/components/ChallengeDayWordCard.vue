<script setup>
defineProps({
  item: {
    type: Object,
    required: true,
  },
  fallbackLetter: {
    type: Function,
    required: true,
  },
});

function wordUrl(item) {
  const query = item.word_list_id ? `?edit=1&list_id=${item.word_list_id}` : '?edit=1';
  return `/words/${item.id}${query}`;
}
</script>

<template>
  <a
    class="panel challenge-day-word"
    :class="item.status === 'correct' ? 'is-correct' : 'is-wrong'"
    :href="wordUrl(item)"
  >
    <span class="challenge-day-result">{{ item.status === 'correct' ? '✓' : '×' }}</span>
    <img v-if="item.image_url" :src="item.image_url" :alt="item.word" loading="lazy">
    <div v-else class="image-fallback">{{ fallbackLetter(item) }}</div>
    <div class="challenge-day-word-body">
      <div>
        <h2>{{ item.word }}</h2>
      </div>
      <strong class="challenge-day-status" :class="item.status === 'correct' ? 'is-correct' : 'is-wrong'">
        {{ item.status === 'correct' ? '正确' : '错误' }}
      </strong>
      <p>{{ item.chinese_definition || item.english_definition || '暂无定义' }}</p>
      <div class="challenge-day-counts">
        <span>对 {{ item.correct_count }}</span>
        <span>错 {{ item.wrong_count }}</span>
      </div>
    </div>
  </a>
</template>
