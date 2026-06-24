<script setup>
import { computed, ref } from "vue";

import WordCard from "./WordCard.vue";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  wordDetailUrl: {
    type: Function,
    required: true,
  },
  imageForWord: {
    type: Function,
    required: true,
  },
  fallbackLetter: {
    type: Function,
    required: true,
  },
});

const activeFilter = ref("all");

const indexedWords = computed(() =>
  (props.data.words || []).map((word, index) => ({
    word,
    index,
  }))
);

const resourceCounts = computed(() => {
  const words = props.data.words || [];
  return {
    all: words.length,
    missingImage: words.filter((word) => !word.image_url).length,
    missingAudio: words.filter((word) => !word.has_audio).length,
    missingAny: words.filter((word) => !word.image_url || !word.has_audio).length,
  };
});

const filterOptions = computed(() => [
  { key: "all", label: "全部", count: resourceCounts.value.all },
  { key: "missingImage", label: "无图片", count: resourceCounts.value.missingImage },
  { key: "missingAudio", label: "无音频", count: resourceCounts.value.missingAudio },
  { key: "missingAny", label: "缺资源", count: resourceCounts.value.missingAny },
]);

const filteredWords = computed(() => {
  if (activeFilter.value === "missingImage") {
    return indexedWords.value.filter(({ word }) => !word.image_url);
  }
  if (activeFilter.value === "missingAudio") {
    return indexedWords.value.filter(({ word }) => !word.has_audio);
  }
  if (activeFilter.value === "missingAny") {
    return indexedWords.value.filter(({ word }) => !word.image_url || !word.has_audio);
  }
  return indexedWords.value;
});
</script>

<template>
  <section class="panel word-resource-filter-panel">
    <div>
      <strong>资源筛选</strong>
      <span>当前 {{ filteredWords.length }} / {{ resourceCounts.all }} 个</span>
    </div>
    <div class="word-resource-filter-actions" role="group" aria-label="资源筛选">
      <button
        v-for="option in filterOptions"
        :key="option.key"
        class="word-resource-filter-button"
        :class="{ active: activeFilter === option.key }"
        type="button"
        @click="activeFilter = option.key"
      >
        <span>{{ option.label }}</span>
        <strong>{{ option.count }}</strong>
      </button>
    </div>
  </section>

  <section v-if="filteredWords.length" class="word-grid">
    <WordCard
      v-for="item in filteredWords"
      :key="item.word.id"
      :word="item.word"
      :index="item.index"
      :href="wordDetailUrl(item.word, data.word_list.id)"
      :image-url="imageForWord(item.word)"
      :fallback-letter="fallbackLetter(item.word)"
    />
  </section>
  <p v-else class="empty-state word-resource-filter-empty">没有符合条件的单词。</p>
</template>
