<script setup>
import { computed, ref, watch } from "vue";
import { BookPlus, FolderPlus, Layers, Search, X } from "lucide-vue-next";
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
const isGroupCreateModalOpen = ref(false);
const searchQuery = ref("");
const searchedQuery = ref("");
const searchResults = ref([]);
const isSearching = ref(false);
const searchError = ref("");
const orderedCards = ref([]);
const newGroupName = ref("");
const groupCreateNotice = ref("");
const isCreatingGroup = ref(false);
const managingCard = ref(null);
const selectedGroupId = ref("");
const groupMoveNotice = ref("");
const isMovingGroup = ref(false);
const draggedListId = ref(null);
const dragOverListId = ref(null);
const isSavingOrder = ref(false);
const orderNotice = ref("");
const dragStartOrder = ref("");
let dragStartCards = [];
let searchTimer = 0;

const trimmedSearchQuery = computed(() => searchQuery.value.trim());
const hasSearched = computed(() => Boolean(searchedQuery.value));
const wordListGroups = computed(() => props.data.groups || []);
const trimmedNewGroupName = computed(() => newGroupName.value.trim());
const groupedListCount = computed(() => wordListGroups.value.reduce((total, group) => total + Number(group.list_count || 0), 0));
const totalWordCount = computed(() => orderedCards.value.reduce((total, card) => total + Number(card.count || 0), 0));

function applyListPagePayload(payload, fallbackCards = orderedCards.value) {
  const cards = payload.cards || fallbackCards || [];
  orderedCards.value = [...cards];
  props.data.cards = orderedCards.value;
  props.data.groups = payload.groups || props.data.groups || [];
  syncUploadOptions(orderedCards.value);
}

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

function groupIndexLabel(index) {
  return String(index + 1).padStart(2, "0");
}

function openListManager(card) {
  managingCard.value = card;
  selectedGroupId.value = card.list?.group_id ? String(card.list.group_id) : "";
  groupMoveNotice.value = "";
}

function closeListManager() {
  managingCard.value = null;
  selectedGroupId.value = "";
  groupMoveNotice.value = "";
}

async function createWordListGroup() {
  const name = trimmedNewGroupName.value;
  if (!name || isCreatingGroup.value) return;
  isCreatingGroup.value = true;
  groupCreateNotice.value = "";
  try {
    const payload = await fetchJson(listApiPaths.createGroup(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name }),
      skipCache: true,
    });
    applyListPagePayload(payload);
    newGroupName.value = "";
    isGroupCreateModalOpen.value = false;
  } catch (error) {
    groupCreateNotice.value = error.message || "单词组创建失败，请稍后再试。";
  } finally {
    isCreatingGroup.value = false;
  }
}

async function moveManagingListToGroup() {
  if (!managingCard.value || isMovingGroup.value) return;
  isMovingGroup.value = true;
  groupMoveNotice.value = "";
  try {
    const payload = await fetchJson(listApiPaths.moveToGroup(managingCard.value.list.id), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ group_id: selectedGroupId.value || null }),
      skipCache: true,
    });
    applyListPagePayload(payload);
    closeListManager();
  } catch (error) {
    groupMoveNotice.value = error.message || "移动失败，请稍后再试。";
  } finally {
    isMovingGroup.value = false;
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
    applyListPagePayload(payload);
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
    <div class="lists-heading-copy">
      <p class="section-kicker">SpeakEasy</p>
      <h1>我的单词表</h1>
      <div class="lists-heading-metrics" aria-label="单词表概览">
        <span>
          <Layers :size="15" aria-hidden="true" />
          {{ wordListGroups.length }} 个单词组
        </span>
        <span>{{ orderedCards.length }} 个单词表</span>
        <span>{{ totalWordCount }} 个单词</span>
      </div>
    </div>
    <div class="lists-page-heading-actions">
      <button class="secondary-button lists-action-button" type="button" @click="isGroupCreateModalOpen = true">
        <FolderPlus :size="17" aria-hidden="true" />
        <span>新建单词组</span>
      </button>
      <button class="primary-action-button lists-action-button" type="button" @click="isCreateModalOpen = true">
        <BookPlus :size="17" aria-hidden="true" />
        <span>新建单词表</span>
      </button>
    </div>
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
  <ListsCreateModal
    v-if="isGroupCreateModalOpen"
    title="新建单词组"
    description="把多个单词表放到同一个组里，适合管理自动分表或同一套词库。"
    @close="isGroupCreateModalOpen = false"
  >
    <form class="list-group-create-form" @submit.prevent="createWordListGroup">
      <label>
        <span>单词组名称</span>
        <input v-model="newGroupName" type="text" placeholder="例如：个人赛冠军词库" autocomplete="off" autofocus>
      </label>
      <button class="primary-action-button" type="submit" :disabled="!trimmedNewGroupName || isCreatingGroup">
        {{ isCreatingGroup ? "创建中" : "创建单词组" }}
      </button>
    </form>
    <p v-if="groupCreateNotice" class="notice">{{ groupCreateNotice }}</p>
  </ListsCreateModal>
  <ListsCreateModal
    v-if="managingCard"
    title="管理单词表"
    :description="managingCard.list.name"
    @close="closeListManager"
  >
    <form class="list-group-manage-form" @submit.prevent="moveManagingListToGroup">
      <label>
        <span>移动到单词组</span>
        <select v-model="selectedGroupId">
          <option value="">不放入单词组</option>
          <option v-for="group in wordListGroups" :key="group.id" :value="String(group.id)">
            {{ group.name }}
          </option>
        </select>
      </label>
      <button class="primary-action-button" type="submit" :disabled="isMovingGroup">
        {{ isMovingGroup ? "保存中" : "保存分组" }}
      </button>
    </form>
    <p v-if="groupMoveNotice" class="notice">{{ groupMoveNotice }}</p>
  </ListsCreateModal>
  <section class="panel word-list-groups-panel">
    <div class="lists-section-head">
      <div>
        <p class="section-kicker">Groups</p>
        <h2>我的单词组</h2>
        <span>{{ groupedListCount }} 个单词表已归组</span>
      </div>
      <button class="secondary-button compact-button lists-action-button" type="button" @click="isGroupCreateModalOpen = true">
        <FolderPlus :size="16" aria-hidden="true" />
        <span>新建单词组</span>
      </button>
    </div>
    <div v-if="wordListGroups.length" class="word-list-group-grid">
      <article v-for="(group, index) in wordListGroups" :key="group.id" class="word-list-group-card">
        <span class="word-list-group-index">{{ groupIndexLabel(index) }}</span>
        <div>
          <strong>{{ group.name }}</strong>
          <span>{{ group.list_count }} 个单词表 · {{ group.word_count }} 个单词</span>
        </div>
      </article>
    </div>
    <p v-else class="empty-state list-group-empty">
      暂无单词组
    </p>
  </section>
  <section class="panel word-list-table-panel">
    <div class="lists-section-head lists-table-head">
      <div>
        <p class="section-kicker">Word Lists</p>
        <h2>我的单词表</h2>
        <span>{{ orderedCards.length }} 个单词表 · {{ totalWordCount }} 个单词</span>
      </div>
    </div>
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
        :sequence="index + 1"
        show-manage
        draggable="true"
        role="listitem"
        :aria-grabbed="draggedListId === card.list.id ? 'true' : 'false'"
        show-challenge
        @manage="openListManager"
        @dragstart="startListDrag(card, $event)"
        @dragover="moveDraggedList(index, $event)"
        @drop.prevent="finishListDrag"
        @dragend="finishListDrag"
      />
    </section>
    <p v-if="isSavingOrder || orderNotice" class="lists-order-notice" :class="{ 'is-error': orderNotice }">
      {{ orderNotice || "正在保存顺序..." }}
    </p>
  </section>
</template>

<style scoped>
.lists-reorder-grid {
  align-items: stretch;
  gap: 18px;
}

.lists-page-heading {
  min-height: 116px;
  border-color: rgba(15, 127, 89, 0.18);
  background:
    radial-gradient(circle at 76% 0%, rgba(243, 190, 95, 0.16), transparent 30%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(232, 247, 241, 0.96));
  box-shadow: 0 18px 46px rgba(15, 28, 36, 0.08);
}

.lists-heading-copy {
  display: grid;
  gap: 9px;
  min-width: 0;
}

.lists-heading-copy h1 {
  margin: 0;
  letter-spacing: 0;
}

.lists-heading-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.lists-heading-metrics span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 28px;
  border: 1px solid rgba(15, 127, 89, 0.12);
  border-radius: 999px;
  padding: 5px 9px;
  color: #0f6b4d;
  background: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  font-weight: 900;
}

.lists-page-heading-actions {
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.lists-action-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
}

.list-word-search-panel {
  margin: -2px 0 18px;
  padding: 10px;
  border-color: rgba(15, 127, 89, 0.13);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 14px 32px rgba(15, 28, 36, 0.05);
}

.list-word-search-form {
  grid-template-columns: minmax(0, 1fr) minmax(96px, auto) auto;
}

.list-word-search-button {
  min-height: 44px;
  border-radius: 12px;
}

.word-list-groups-panel {
  position: relative;
  display: grid;
  gap: 14px;
  margin-bottom: 18px;
  overflow: hidden;
  padding: 18px;
  border-color: rgba(15, 127, 89, 0.18);
  background:
    radial-gradient(circle at 100% 0%, rgba(15, 127, 89, 0.1), transparent 30%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(235, 248, 242, 0.96));
  box-shadow: 0 16px 38px rgba(15, 28, 36, 0.06);
}

.word-list-groups-panel::before {
  content: "";
  position: absolute;
  inset: auto 18px 0 18px;
  height: 3px;
  border-radius: 999px 999px 0 0;
  background: linear-gradient(90deg, rgba(15, 127, 89, 0.52), rgba(243, 190, 95, 0.35), transparent);
}

.lists-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.lists-section-head h2 {
  margin: 0;
  color: #111827;
  font-size: clamp(22px, 3vw, 30px);
  line-height: 1.1;
}

.lists-section-head > div {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.lists-section-head > span {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 6px 10px;
  color: #0f6b4d;
  background: rgba(29, 127, 91, 0.11);
  font-size: 13px;
  font-weight: 900;
}

.lists-section-head > div > span {
  color: #536579;
  font-size: 13px;
  font-weight: 850;
}

.word-list-group-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}

.word-list-group-card {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  min-height: 92px;
  border: 1px solid rgba(15, 127, 89, 0.16);
  border-radius: 18px;
  padding: 14px;
  color: #0f172a;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(229, 246, 238, 0.9));
  box-shadow: 0 10px 24px rgba(15, 28, 36, 0.06);
  transition: transform 0.16s ease, border-color 0.16s ease, background 0.16s ease, color 0.16s ease;
}

.word-list-group-card::after {
  content: "";
  position: absolute;
  top: 12px;
  right: 12px;
  width: 38px;
  height: 18px;
  border-radius: 999px;
  background: rgba(243, 190, 95, 0.16);
}

.word-list-group-card:hover {
  border-color: rgba(15, 127, 89, 0.78);
  color: #fff;
  background: linear-gradient(135deg, #0f7f59, #0b5f43);
  transform: translateY(-1px);
}

.word-list-group-card:hover strong,
.word-list-group-card:hover span,
.word-list-group-card:hover div span {
  color: #fff;
}

.word-list-group-card:hover::after {
  background: rgba(255, 255, 255, 0.14);
}

.word-list-group-index {
  display: inline-grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 16px;
  color: #0f6b4d;
  background: #e8f7ef;
  font-size: 15px;
  font-weight: 1000;
}

.word-list-group-card:hover .word-list-group-index {
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
}

.word-list-group-card div {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.word-list-group-card strong {
  overflow: hidden;
  color: #111827;
  font-size: 18px;
  font-weight: 1000;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.word-list-group-card div span {
  color: #536579;
  font-size: 13px;
  font-weight: 850;
}

.list-group-empty {
  display: grid;
  place-items: center;
  min-height: 84px;
  margin: 0;
  border: 1px dashed rgba(15, 127, 89, 0.2);
  border-radius: 16px;
  color: #6b7c8d;
  background: rgba(255, 255, 255, 0.62);
  font-weight: 900;
}

.word-list-table-panel {
  display: grid;
  gap: 16px;
  margin-bottom: 18px;
  padding: 18px;
  border-color: rgba(15, 127, 89, 0.13);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(249, 253, 250, 0.92));
  box-shadow: 0 16px 40px rgba(15, 28, 36, 0.06);
}

.lists-table-head {
  margin: 0;
  padding: 0;
}

.word-list-table-panel :deep(.list-card) {
  border-color: rgba(15, 127, 89, 0.14);
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 14px 32px rgba(15, 28, 36, 0.07);
}

.word-list-table-panel :deep(.list-card:hover) {
  border-color: rgba(15, 127, 89, 0.38);
  box-shadow: 0 20px 42px rgba(15, 28, 36, 0.11);
}

.word-list-table-panel :deep(.word-card-body) {
  min-height: 62px;
}

.word-list-table-panel :deep(.challenge-card-actions) {
  background: rgba(255, 255, 255, 0.96);
}

.list-group-create-form,
.list-group-manage-form {
  display: grid;
  gap: 14px;
}

.list-group-create-form label,
.list-group-manage-form label {
  display: grid;
  gap: 7px;
  color: #536579;
  font-size: 13px;
  font-weight: 900;
}

.list-group-create-form input,
.list-group-manage-form select {
  min-height: 44px;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0 12px;
  color: var(--text);
  background: #fff;
  font: inherit;
  font-weight: 850;
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
  margin: 0;
  color: #0b6f4c;
  font-size: 13px;
  font-weight: 800;
}

.lists-order-notice.is-error {
  color: #b42318;
}

@media (max-width: 720px) {
  .lists-page-heading-actions,
  .lists-section-head {
    align-items: stretch;
    flex-direction: column;
  }

  .lists-page-heading {
    align-items: stretch;
  }

  .lists-heading-metrics {
    align-items: stretch;
    flex-direction: column;
  }

  .lists-page-heading-actions > button,
  .lists-section-head > button {
    width: 100%;
  }

  .list-word-search-form {
    grid-template-columns: 1fr;
  }

  .word-list-group-grid {
    grid-template-columns: 1fr;
  }
}
</style>
