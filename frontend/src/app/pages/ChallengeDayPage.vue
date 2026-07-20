<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import ChallengeDayStats from "../components/ChallengeDayStats.vue";
import ChallengeDayWordCard from "../components/ChallengeDayWordCard.vue";

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

const activeFilter = ref("all");
const selectedListKey = ref(readSelectedListKey());

function itemListKey(item) {
  return item.word_list_id ? String(item.word_list_id) : "none";
}

function readSelectedListKey() {
  const params = new URLSearchParams(window.location.search);
  return params.get("list_id") || params.get("list_key") || "";
}

function syncSelectedListFromUrl() {
  selectedListKey.value = readSelectedListKey();
  activeFilter.value = "all";
}

function updateSelectedListUrl(summary) {
  const url = new URL(window.location.href);
  url.searchParams.delete("list_id");
  url.searchParams.delete("list_key");
  if (summary?.id) {
    url.searchParams.set("list_id", String(summary.id));
  } else if (summary?.key) {
    url.searchParams.set("list_key", summary.key);
  }
  history.pushState(null, "", `${url.pathname}${url.search}`);
}

function selectList(summary) {
  selectedListKey.value = summary.key;
  activeFilter.value = "all";
  updateSelectedListUrl(summary);
}

function clearSelectedList() {
  selectedListKey.value = "";
  activeFilter.value = "all";
  const url = new URL(window.location.href);
  url.searchParams.delete("list_id");
  url.searchParams.delete("list_key");
  history.pushState(null, "", `${url.pathname}${url.search}`);
}

const words = computed(() => props.data.words || []);

const listSummaries = computed(() => {
  if (Array.isArray(props.data.list_summaries) && props.data.list_summaries.length) {
    return props.data.list_summaries;
  }
  const summaryMap = new Map();
  words.value.forEach((item) => {
    const key = itemListKey(item);
    if (!summaryMap.has(key)) {
      summaryMap.set(key, {
        key,
        id: item.word_list_id || null,
        name: item.word_list_name || "未归属单词表",
        word_count: 0,
        correct: 0,
        wrong: 0,
        wrong_attempts: 0,
        corrected: 0,
        pending: 0,
      });
    }
    const summary = summaryMap.get(key);
    summary.word_count += 1;
    summary.correct += Number(item.correct_count || 0);
    summary.wrong_attempts += Number(item.wrong_count || 0);
    if (item.was_wrong || item.wrong_count) summary.wrong += 1;
    if (item.corrected) summary.corrected += 1;
    if (item.was_wrong && !item.corrected) summary.pending += 1;
  });
  return Array.from(summaryMap.values());
});

const selectedList = computed(() => listSummaries.value.find((item) => item.key === selectedListKey.value) || null);
const scopedWords = computed(() => {
  if (!selectedList.value) return words.value;
  return words.value.filter((item) => itemListKey(item) === selectedList.value.key);
});

const filteredWords = computed(() => {
  if (activeFilter.value === "all") return scopedWords.value;
  if (activeFilter.value === "wrong") return scopedWords.value.filter((item) => item.was_wrong || item.status === "wrong");
  if (activeFilter.value === "pending") return scopedWords.value.filter((item) => item.was_wrong && !item.corrected);
  return scopedWords.value.filter((item) => item.status === activeFilter.value);
});

const wrongChallengeCount = computed(
  () => props.data.wrong_challenge_count ?? props.data.correction_pending ?? props.data.wrong ?? 0,
);
const wrongChallengeUrl = computed(() => {
  if (!props.data.wrong_word_list_id || !wrongChallengeCount.value) return "";
  const params = new URLSearchParams({
    daily_count: String(wrongChallengeCount.value),
    start_count: "0",
    wrong_date: props.data.date,
    restart: "1",
  });
  return `/challenge/${props.data.wrong_word_list_id}?${params.toString()}`;
});

function setFilter(filter) {
  activeFilter.value = activeFilter.value === filter ? "all" : filter;
}

watch(
  listSummaries,
  (summaries) => {
    if (!selectedListKey.value) return;
    if (!summaries.some((item) => item.key === selectedListKey.value)) {
      selectedListKey.value = "";
    }
  },
  { immediate: true },
);

onMounted(() => {
  window.addEventListener("popstate", syncSelectedListFromUrl);
});

onBeforeUnmount(() => {
  window.removeEventListener("popstate", syncSelectedListFromUrl);
});
</script>

<template>
  <ChallengeDayStats
    :correct="data.correct"
    :wrong="data.wrong"
    :wrong-attempts="data.wrong_attempts"
    :corrected="data.corrected"
    :correction-pending="data.correction_pending"
    :active-filter="activeFilter"
    :wrong-challenge-url="wrongChallengeUrl"
    :wrong-challenge-count="wrongChallengeCount"
    :go="go"
    @filter="setFilter"
  />
  <section v-if="data.recovery_note" class="notice">
    {{ data.recovery_note }}
  </section>
  <section v-if="!selectedList" class="panel challenge-day-list-overview">
    <div class="challenge-day-list-heading">
      <div>
        <p class="section-kicker">Practice Lists</p>
        <h2>今日练习的单词表</h2>
        <p>{{ data.date }} 的挑战先按单词表汇总，点进去再看每个单词的正确与错误。</p>
      </div>
      <strong>{{ listSummaries.length }} 个单词表</strong>
    </div>
    <div v-if="listSummaries.length" class="challenge-day-list-grid">
      <button
        v-for="summary in listSummaries"
        :key="summary.key"
        class="challenge-day-list-card"
        type="button"
        @click="selectList(summary)"
      >
        <span class="challenge-day-list-title">{{ summary.name }}</span>
        <span class="challenge-day-list-count">{{ summary.word_count }} 个单词</span>
        <span class="challenge-day-list-metrics">
          <em class="is-correct">正确 {{ summary.correct }}</em>
          <em class="is-wrong">错误 {{ summary.wrong }}</em>
          <em class="is-pending">待纠正 {{ summary.pending }}</em>
        </span>
      </button>
    </div>
    <p v-else class="empty-state challenge-day-filter-empty">
      这一天还没有单词表练习记录。
    </p>
  </section>

  <section v-else class="panel challenge-day-detail-head">
    <div>
      <p class="section-kicker">Word Results</p>
      <h2>{{ selectedList.name }}</h2>
      <p>
        {{ selectedList.word_count }} 个单词 · 正确 {{ selectedList.correct }} · 错误 {{ selectedList.wrong }}
      </p>
    </div>
    <button class="secondary-button" type="button" @click="clearSelectedList">返回单词表汇总</button>
  </section>

  <section v-if="selectedList" class="challenge-day-grid">
    <ChallengeDayWordCard
      v-for="item in filteredWords"
      :key="`${item.id}-${item.status}`"
      :item="item"
      :day="data.date"
      :fallback-letter="fallbackLetter"
    />
    <p v-if="!filteredWords.length" class="empty-state challenge-day-filter-empty">
      当前筛选没有单词。
    </p>
  </section>
</template>
