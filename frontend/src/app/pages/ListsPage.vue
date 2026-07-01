<script setup>
import { computed, ref, watch } from "vue";
import { Search, X } from "lucide-vue-next";
import ListsCreateModal from "../components/ListsCreateModal.vue";
import ListsToolsPanel from "../components/ListsToolsPanel.vue";
import WordListCard from "../components/WordListCard.vue";
import { listApiPaths } from "../listApiPaths.js";
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
const orderedCards = ref([]);
const draggedListId = ref(null);
const dragOverListId = ref(null);
const isSavingOrder = ref(false);
const orderNotice = ref("");
const dragStartOrder = ref("");
let dragStartCards = [];
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

function cardIds(cards = orderedCards.value) {
  return cards.map((card) => Number(card.list.id)).filter(Boolean);
}

function syncUploadOptions(cards = orderedCards.value) {
  if (props.uploadOptions) {
    props.uploadOptions.word_lists = cards.map((card) => card.list);
  }
}

function moveCard(fromIndex, toIndex) {
  if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) return;
  const nextCards = [...orderedCards.value];
  const [moved] = nextCards.splice(fromIndex, 1);
  nextCards.splice(toIndex, 0, moved);
  orderedCards.value = nextCards;
}

function startListDrag(card, event) {
  draggedListId.value = card.list.id;
  dragOverListId.value = card.list.id;
  dragStartOrder.value = cardIds().join(",");
  dragStartCards = [...orderedCards.value];
  orderNotice.value = "";
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", String(card.list.id));
  }
}

function moveDraggedList(targetIndex, event) {
  event.preventDefault();
  if (!draggedListId.value) return;
  const fromIndex = orderedCards.value.findIndex((card) => card.list.id === draggedListId.value);
  const targetCard = orderedCards.value[targetIndex];
  if (!targetCard || fromIndex < 0) return;
  dragOverListId.value = targetCard.list.id;
  moveCard(fromIndex, targetIndex);
}

async function saveListOrder(ids) {
  isSavingOrder.value = true;
  orderNotice.value = "";
  try {
    const payload = await fetchJson(listApiPaths.reorder(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ordered_ids: ids }),
      skipCache: true,
    });
    orderedCards.value = payload.cards || orderedCards.value;
    props.data.cards = orderedCards.value;
    syncUploadOptions();
  } catch (error) {
    orderedCards.value = dragStartCards;
    props.data.cards = dragStartCards;
    syncUploadOptions(dragStartCards);
    orderNotice.value = error.message || "顺序保存失败，请稍后重试。";
  } finally {
    isSavingOrder.value = false;
  }
}

async function finishListDrag() {
  if (!draggedListId.value) return;
  const nextOrder = cardIds().join(",");
  const nextIds = cardIds();
  draggedListId.value = null;
  dragOverListId.value = null;
  if (nextOrder && nextOrder !== dragStartOrder.value) {
    await saveListOrder(nextIds);
  }
  dragStartOrder.value = "";
  dragStartCards = [];
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

watch(
  () => props.data.cards,
  (cards) => {
    if (draggedListId.value) return;
    orderedCards.value = [...(cards || [])];
    syncUploadOptions(orderedCards.value);
  },
  { immediate: true }
);
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
  <section class="word-grid lists-reorder-grid" role="list" @dragover.prevent>
    <WordListCard
      v-for="(card, index) in orderedCards"
      :key="card.list.id"
      class="lists-reorder-card"
      :class="{
        'is-list-dragging': draggedListId === card.list.id,
        'is-list-drag-over': dragOverListId === card.list.id && draggedListId !== card.list.id,
      }"
      :card="card"
      :fallback-letter="fallbackLetter"
      :go="go"
      draggable="true"
      role="listitem"
      :aria-grabbed="draggedListId === card.list.id ? 'true' : 'false'"
      show-challenge
      @dragstart="startListDrag(card, $event)"
      @dragover="moveDraggedList(index, $event)"
      @drop.prevent="finishListDrag"
      @dragend="finishListDrag"
    />
  </section>
  <p v-if="isSavingOrder || orderNotice" class="lists-order-notice" :class="{ 'is-error': orderNotice }">
    {{ orderNotice || "正在保存顺序..." }}
  </p>
</template>

<style scoped>
.lists-reorder-grid {
  align-items: stretch;
}

.lists-reorder-card {
  cursor: grab;
  transition: transform 0.16s ease, box-shadow 0.16s ease, opacity 0.16s ease;
}

.lists-reorder-card :deep(.list-card-link) {
  cursor: grab;
}

.lists-reorder-card:active {
  cursor: grabbing;
}

.lists-reorder-card:active :deep(.list-card-link) {
  cursor: grabbing;
}

.lists-reorder-card.is-list-dragging {
  opacity: 0.56;
  transform: scale(0.985);
}

.lists-reorder-card.is-list-drag-over {
  box-shadow: 0 18px 34px rgba(15, 127, 89, 0.2);
  outline: 2px solid rgba(15, 127, 89, 0.45);
  outline-offset: 3px;
}

.lists-order-notice {
  margin: -4px 0 14px;
  color: #0b6f4c;
  font-size: 13px;
  font-weight: 800;
}

.lists-order-notice.is-error {
  color: #b42318;
}
</style>
