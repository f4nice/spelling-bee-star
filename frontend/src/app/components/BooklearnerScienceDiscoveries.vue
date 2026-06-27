<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  book: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
  loadScienceDiscoveries: {
    type: Function,
    required: true,
  },
});

const levels = [
  { value: "L300-L500", label: "L300-L500 入门" },
  { value: "L500-L700", label: "L500-L700 进阶" },
  { value: "L700-L900", label: "L700-L900 挑战" },
];
const topics = ["全部", "动物", "植物", "人体", "微生物", "地球", "太空", "工程"];
const loading = ref(false);
const science = computed(() => props.book.science || {});
const selectedLevel = ref(science.value.level || "L500-L700");
const selectedTopic = ref(science.value.topic || "全部");

watch(
  science,
  (value) => {
    selectedLevel.value = value.level || selectedLevel.value;
    selectedTopic.value = value.topic || selectedTopic.value;
  },
  { deep: true },
);

async function reload(overrides = {}) {
  loading.value = true;
  try {
    await props.loadScienceDiscoveries({
      level: overrides.level || selectedLevel.value,
      topic: overrides.topic || selectedTopic.value,
      batch: overrides.batch ?? science.value.batch ?? 0,
    });
  } finally {
    loading.value = false;
  }
}

function changeLevel() {
  reload({ level: selectedLevel.value, batch: 0 });
}

function changeTopic() {
  reload({ topic: selectedTopic.value, batch: 0 });
}

function nextBatch() {
  reload({ batch: Number(science.value.batch || 0) + 1 });
}

function openDiscovery(item) {
  props.go(`/booklearner/science/${item.slug}`);
}
</script>

<template>
  <section class="panel science-discovery-panel">
    <div class="science-discovery-head">
      <div>
        <span class="eyebrow">DAILY DISCOVERIES</span>
        <h2>今日 5 个知识点</h2>
        <p>每天缓存一组稳定内容，适合检查、复习和继续阅读。</p>
      </div>
      <button type="button" class="secondary-button science-refresh-button" :disabled="loading" @click="nextBatch">
        {{ loading ? "生成中..." : "换一批" }}
      </button>
    </div>

    <div class="science-toolbar">
      <label>
        <span>Choose Level</span>
        <select v-model="selectedLevel" @change="changeLevel">
          <option v-for="item in levels" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
      </label>
      <label>
        <span>Science Topics</span>
        <select v-model="selectedTopic" @change="changeTopic">
          <option v-for="item in topics" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <div class="science-cache-note">
        <strong>{{ science.date || "今日" }}</strong>
        <span>{{ science.levelLabel || selectedLevel }} · {{ science.topic || selectedTopic }}</span>
      </div>
    </div>

    <div class="science-source-strip">
      <span>知识来源</span>
      <a v-for="item in science.sources" :key="item.name" :href="item.url" target="_blank" rel="noreferrer">
        {{ item.name }}
      </a>
    </div>

    <div class="science-discovery-grid">
      <button
        v-for="item in science.items"
        :key="item.slug"
        type="button"
        class="science-discovery-card"
        @click="openDiscovery(item)"
      >
        <div class="science-card-topline">
          <span>{{ item.topic }}</span>
          <small>{{ item.source }}</small>
        </div>
        <h3>{{ item.title }}</h3>
        <p>{{ item.summary }}</p>
        <div class="science-word-chips" aria-label="Words I Learned">
          <span v-for="word in item.words" :key="word.word">{{ word.word }}</span>
        </div>
      </button>
    </div>

    <p v-if="!science.items?.length" class="notice">还没有知识点，稍后刷新即可。</p>
  </section>
</template>
