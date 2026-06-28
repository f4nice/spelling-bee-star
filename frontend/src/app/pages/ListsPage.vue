<script setup>
import { computed, ref, watch } from "vue";
import { Search, X } from "lucide-vue-next";
import ListsCreateModal from "../components/ListsCreateModal.vue";
import ListsToolsPanel from "../components/ListsToolsPanel.vue";
import WordListCard from "../components/WordListCard.vue";
import { routeApiPaths } from "../routeApiPaths.js";
import { fetchJson } from "../utils.js";

const props = defineProps([
  "data",
  "uploadOptions",
  "uploadForm",
  "batchImageState",
  "submitUpload",
  "submitBatchImages",
  "fallbackLetter",
  "go",
]);

const isCreateModalOpen = ref(false);
const searchQuery = ref("");
const searchedQuery = ref("");
const searchResults = ref([]);
const isSearching = ref(false);
const searchError = ref("");
let searchTimer = 0;

const trimmedSearchQuery = computed(() => searchQuery.value.trim());
const hasSearched = computed(() => Boolean(searchedQuery.value));

function firstDefinition(result) {
  return result.word?.chinese_definition || result.word?.english_definition || result.word?.part_of_speech || "";
}

function wordDetailPath(result) {
  const firstList = result.lists?.[0];
  const params = new URLSearchParams({ edit: "1" });
  if (firstList?.id) params.set("list_id", firstList.id);
  return `/words/${result.word.id}?${params.toString()}`;
}

function openWord(result) {
  props.go(wordDetailPath(result));
}

function openList(list) {
  props.go(`/lists/${list.id}`);
}

function clearSearch() {
  searchQuery.value = "";
  searchedQuery.value = "";
  searchResults.value = [];
  searchError.value = "";
  window.clearTimeout(searchTimer);
}

async function runSearch() {
  const query = trimmedSearchQuery.value;
  if (!query) {
    clearSearch();
    return;
  }
  isSearching.value = true;
  searchError.value = "";
  try {
    const payload = await fetchJson(routeApiPaths.listSearch(query), { skipCache: true });
    searchedQuery.value = payload.query || query;
    searchResults.value = payload.results || [];
  } catch (error) {
    searchError.value = error.message || "搜索失败";
    searchResults.value = [];
  } finally {
    isSearching.value = false;
  }
}

watch(searchQuery, () => {
  window.clearTimeout(searchTimer);
  if (!trimmedSearchQuery.value) {
    searchedQuery.value = "";
    searchResults.value = [];
    searchError.value = "";
    return;
  }
  searchTimer = window.setTimeout(runSearch, 240);
});
</script>

<template>
  <section class="panel app-page-heading lists-page-heading">
    <div>
      <p class="section-kicker">SpeakEasy</p>
      <h1>我的单词表</h1>
    </div>
    <button class="primary-action-button" type="button" @click="isCreateModalOpen = true">
      新建单词表
    </button>
  </section>
  <section class="panel list-word-search-panel">
    <form class="list-word-search-form" @submit.prevent="runSearch">
      <label class="list-word-search-field" aria-label="搜索单词">
        <Search :size="19" aria-hidden="true" />
        <input v-model="searchQuery" type="search" placeholder="输入单词，查看所在单词表" autocomplete="off" />
      </label>
      <button class="primary-action-button list-word-search-button" type="submit" :disabled="!trimmedSearchQuery || isSearching">
        <Search :size="18" aria-hidden="true" />
        <span>{{ isSearching ? "搜索中" : "搜索" }}</span>
      </button>
      <button
        v-if="searchQuery"
        class="secondary-button list-word-clear-button"
        type="button"
        aria-label="清空搜索"
        @click="clearSearch"
      >
        <X :size="18" aria-hidden="true" />
      </button>
    </form>
    <p v-if="searchError" class="notice list-word-search-notice">{{ searchError }}</p>
    <div v-else-if="searchResults.length" class="list-word-search-results">
      <article v-for="result in searchResults" :key="result.word.id" class="list-word-search-result">
        <button type="button" class="list-word-search-word" @click="openWord(result)">
          <strong>{{ result.word.word }}</strong>
          <span v-if="firstDefinition(result)">{{ firstDefinition(result) }}</span>
        </button>
        <div class="list-word-search-lists" aria-label="所在单词表">
          <button v-for="list in result.lists" :key="list.id" type="button" @click="openList(list)">
            {{ list.name }}
          </button>
        </div>
      </article>
    </div>
    <p v-else-if="hasSearched && !isSearching" class="empty-state list-word-search-empty">
      没有找到 “{{ searchedQuery }}”。
    </p>
  </section>
  <ListsCreateModal v-if="isCreateModalOpen" @close="isCreateModalOpen = false">
    <ListsToolsPanel
      :data="data"
      :upload-options="uploadOptions"
      :upload-form="uploadForm"
      :batch-image-state="batchImageState"
      :submit-upload="submitUpload"
      :submit-batch-images="submitBatchImages"
    />
  </ListsCreateModal>
  <section class="word-grid">
    <WordListCard
      v-for="card in data.cards"
      :key="card.list.id"
      :card="card"
      :fallback-letter="fallbackLetter"
      :go="go"
      show-challenge
    />
  </section>
</template>
