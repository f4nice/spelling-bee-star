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
  aiImageJob: {
    type: Object,
    default: null,
  },
  generateListAiImages: {
    type: Function,
    required: true,
  },
});

const activeFilter = ref("all");
const aiJobNotice = ref("");

const indexedWords = computed(() =>
  (props.data.words || []).map((word, index) => ({
    word,
    index: Number(word.display_index || index + 1) - 1,
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

const aiImageJob = computed(() => props.aiImageJob || null);
const aiImageTotal = computed(() => Math.max(Number(aiImageJob.value?.total || 0), 0));
const aiImageDone = computed(() => Math.max(Number(aiImageJob.value?.done || 0), 0));
const aiImageProgress = computed(() => {
  if (!aiImageTotal.value) return aiImageJob.value?.status === "complete" ? 100 : 0;
  return Math.min(100, Math.round((aiImageDone.value / aiImageTotal.value) * 100));
});
const isAiImageRunning = computed(() => ["queued", "running"].includes(aiImageJob.value?.status));
const aiImageJobClass = computed(() => ({
  "is-syncing": isAiImageRunning.value,
  "is-complete": aiImageJob.value?.status === "complete",
  "has-error": aiImageJob.value?.status === "failed",
}));
const aiImageJobText = computed(() => {
  if (!aiImageJob.value) return "默认模型：阿里 · wan2.6-t2i，只处理没有图片的单词。";
  return aiImageJob.value.message || "正在批量生成 AI 图片";
});

async function startBatchAiImages() {
  if (isAiImageRunning.value || !resourceCounts.value.missingImage) return;
  aiJobNotice.value = "";
  try {
    await props.generateListAiImages();
  } catch (error) {
    aiJobNotice.value = error.message || "批量 AI 生图启动失败";
  }
}
</script>

<template>
  <section class="panel word-resource-filter-panel">
    <div class="word-resource-filter-top">
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
    </div>
    <div class="list-ai-image-toolbar" :class="aiImageJobClass">
      <div class="list-ai-image-summary">
        <strong>批量 AI 图片</strong>
        <span>{{ aiImageJobText }}</span>
      </div>
      <div v-if="aiImageJob" class="sync-progress-wrap list-ai-image-progress">
        <div class="sync-progress" aria-hidden="true"><span :style="{ width: `${aiImageProgress}%` }"></span></div>
        <strong>{{ aiImageDone }} / {{ aiImageTotal }}</strong>
      </div>
      <button
        class="primary-action-button list-ai-image-button"
        type="button"
        :disabled="isAiImageRunning || !resourceCounts.missingImage"
        @click="startBatchAiImages"
      >
        {{ isAiImageRunning ? "生成中" : "批量生成图片" }}
      </button>
    </div>
    <p v-if="aiJobNotice" class="notice list-ai-image-notice">{{ aiJobNotice }}</p>
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
