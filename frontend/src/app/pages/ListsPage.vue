<script setup>
import { computed, ref, watch } from "vue";
import { ArrowLeft, BookPlus, FolderPlus, Layers, Search, Trash2, X } from "lucide-vue-next";
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
const activeGroupId = ref("");
const dragOverGroupId = ref("");
const isDroppingOnGroup = ref(false);
const groupDeletePassword = ref("");
const groupDeleteNotice = ref("");
const isDeletingGroup = ref(false);
let dragStartCards = [];
let searchTimer = 0;

const trimmedSearchQuery = computed(() => searchQuery.value.trim());
const hasSearched = computed(() => Boolean(searchedQuery.value));
const wordListGroups = computed(() => props.data.groups || []);
const trimmedNewGroupName = computed(() => newGroupName.value.trim());
const trimmedGroupDeletePassword = computed(() => groupDeletePassword.value.trim());
const groupedListCount = computed(() => wordListGroups.value.reduce((total, group) => total + Number(group.list_count || 0), 0));
const totalWordCount = computed(() => orderedCards.value.reduce((total, card) => total + Number(card.count || 0), 0));
const activeGroup = computed(() => wordListGroups.value.find((group) => String(group.id) === String(activeGroupId.value)) || null);
const ungroupedCards = computed(() => orderedCards.value.filter((card) => !card.list?.group_id));
const activeGroupCards = computed(() => {
  if (!activeGroup.value) return [];
  return orderedCards.value.filter((card) => String(card.list?.group_id || "") === String(activeGroup.value.id));
});
const displayedCards = computed(() => (activeGroup.value ? activeGroupCards.value : ungroupedCards.value));
const displayedWordCount = computed(() => displayedCards.value.reduce((total, card) => total + Number(card.count || 0), 0));
const displayedListTitle = computed(() => (activeGroup.value ? activeGroup.value.name : "我的单词表"));
const displayedListDescription = computed(() => (
  activeGroup.value
    ? "这个专题里只显示当前单词组的单词表。"
    : "已放入单词组的单词表不在这里重复显示。"
));

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

function displayedCardIds() {
  return cardIds(displayedCards.value);
}

function syncUploadOptions(cards = orderedCards.value) {
  if (props.uploadOptions) {
    props.uploadOptions.word_lists = cards.map((card) => card.list);
  }
}

function groupIndexLabel(index) {
  return String(index + 1).padStart(2, "0");
}

function selectWordListGroup(group) {
  activeGroupId.value = String(group.id);
  orderNotice.value = "";
  groupDeletePassword.value = "";
  groupDeleteNotice.value = "";
}

function clearActiveWordListGroup() {
  activeGroupId.value = "";
  orderNotice.value = "";
  groupDeletePassword.value = "";
  groupDeleteNotice.value = "";
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

async function deleteActiveWordListGroup() {
  if (!activeGroup.value || !trimmedGroupDeletePassword.value || isDeletingGroup.value) return;
  isDeletingGroup.value = true;
  groupDeleteNotice.value = "";
  try {
    const deletedGroupId = activeGroup.value.id;
    const payload = await fetchJson(listApiPaths.deleteGroup(deletedGroupId), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password: trimmedGroupDeletePassword.value }),
      skipCache: true,
    });
    groupDeletePassword.value = "";
    activeGroupId.value = "";
    applyListPagePayload(payload);
  } catch (error) {
    groupDeleteNotice.value = error.message || "单词组删除失败，请稍后再试。";
  } finally {
    isDeletingGroup.value = false;
  }
}

function resetListDragState() {
  draggedListId.value = null;
  dragOverListId.value = null;
  dragOverGroupId.value = "";
  dragStartOrder.value = "";
  dragStartCards = [];
}

async function moveDraggedListToGroup(group, event) {
  event.preventDefault();
  event.stopPropagation();
  const wordListId = draggedListId.value;
  if (!wordListId || !group?.id) {
    resetListDragState();
    return;
  }
  const card = orderedCards.value.find((item) => Number(item.list.id) === Number(wordListId));
  if (!card || String(card.list?.group_id || "") === String(group.id)) {
    resetListDragState();
    return;
  }
  dragOverGroupId.value = "";
  isDroppingOnGroup.value = true;
  try {
    const payload = await fetchJson(listApiPaths.moveToGroup(wordListId), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ group_id: group.id }),
      skipCache: true,
    });
    activeGroupId.value = String(group.id);
    applyListPagePayload(payload);
  } catch (error) {
    orderNotice.value = error.message || "移动到单词组失败，请稍后再试。";
  } finally {
    isDroppingOnGroup.value = false;
    resetListDragState();
  }
}

function moveCard(fromIndex, toIndex) {
  if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) return;
  const scopedCards = [...displayedCards.value];
  const targetScopeIds = new Set(scopedCards.map((card) => Number(card.list.id)));
  const nextCards = [...scopedCards];
  const [moved] = nextCards.splice(fromIndex, 1);
  nextCards.splice(toIndex, 0, moved);
  let nextIndex = 0;
  orderedCards.value = orderedCards.value.map((card) => {
    if (!targetScopeIds.has(Number(card.list.id))) return card;
    return nextCards[nextIndex++] || card;
  });
}

function startListDrag(card, event) {
  draggedListId.value = card.list.id;
  dragOverListId.value = card.list.id;
  dragStartOrder.value = displayedCardIds().join(",");
  dragStartCards = [...orderedCards.value];
  orderNotice.value = "";
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", String(card.list.id));
  }
}

function enterGroupDropTarget(group, event) {
  if (!draggedListId.value) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
  dragOverGroupId.value = String(group.id);
}

function leaveGroupDropTarget(group, event) {
  const nextTarget = event?.relatedTarget;
  if (nextTarget instanceof Node && event.currentTarget?.contains(nextTarget)) return;
  if (dragOverGroupId.value === String(group.id)) {
    dragOverGroupId.value = "";
  }
}

function moveDraggedList(targetIndex, event) {
  event.preventDefault();
  if (!draggedListId.value) return;
  const visibleCards = displayedCards.value;
  const fromIndex = visibleCards.findIndex((card) => card.list.id === draggedListId.value);
  const targetCard = visibleCards[targetIndex];
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
  if (isDroppingOnGroup.value) return;
  if (dragOverGroupId.value) {
    resetListDragState();
    return;
  }
  const nextOrder = displayedCardIds().join(",");
  const nextIds = cardIds(orderedCards.value);
  draggedListId.value = null;
  dragOverListId.value = null;
  if (nextOrder && nextOrder !== dragStartOrder.value) {
    await saveListOrder(nextIds);
  }
  dragStartOrder.value = "";
  dragStartCards = [];
  dragOverGroupId.value = "";
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

watch(wordListGroups, (groups) => {
  if (!activeGroupId.value) return;
  const exists = groups.some((group) => String(group.id) === String(activeGroupId.value));
  if (!exists) activeGroupId.value = "";
});
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
      <button class="primary-action-button list-group-create-submit" type="submit" :disabled="!trimmedNewGroupName || isCreatingGroup">
        <FolderPlus :size="17" aria-hidden="true" />
        <span>{{ isCreatingGroup ? "创建中" : "创建单词组" }}</span>
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
    <div class="lists-section-head word-list-groups-head">
      <div class="lists-section-copy">
        <p class="section-kicker">Groups</p>
        <h2>我的单词组</h2>
        <span>把同一套词库收在一个组里，分表管理会更清楚。</span>
      </div>
      <div class="lists-section-meta">
        <span>{{ wordListGroups.length }} 个组</span>
        <strong>{{ groupedListCount }}</strong>
        <span>个单词表已归组</span>
      </div>
    </div>
    <div v-if="wordListGroups.length" class="word-list-group-grid">
      <button
        v-for="(group, index) in wordListGroups"
        :key="group.id"
        class="word-list-group-card"
        :class="{
          'is-active': activeGroup?.id === group.id,
          'is-drop-target': dragOverGroupId === String(group.id),
        }"
        type="button"
        :title="`查看 ${group.name}`"
        @click="selectWordListGroup(group)"
        @dragenter="enterGroupDropTarget(group, $event)"
        @dragover="enterGroupDropTarget(group, $event)"
        @dragleave="leaveGroupDropTarget(group, $event)"
        @drop="moveDraggedListToGroup(group, $event)"
      >
        <span class="word-list-group-index">{{ groupIndexLabel(index) }}</span>
        <div>
          <strong>{{ group.name }}</strong>
          <span>{{ group.list_count }} 个单词表 · {{ group.word_count }} 个单词</span>
        </div>
        <span class="word-list-group-action">查看专题</span>
      </button>
    </div>
    <p v-else class="empty-state list-group-empty">
      暂无单词组
    </p>
  </section>
  <section class="panel word-list-table-panel">
    <div class="lists-section-head lists-table-head">
      <div class="lists-section-copy">
        <p class="section-kicker">Word Lists</p>
        <h2>{{ displayedListTitle }}</h2>
        <span>{{ displayedListDescription }}</span>
      </div>
      <div class="lists-table-actions">
        <div class="lists-table-actions-row">
          <div class="lists-section-meta">
            <span>{{ displayedCards.length }} 个单词表</span>
            <strong>{{ displayedWordCount }}</strong>
            <span>个单词</span>
          </div>
          <button v-if="activeGroup" class="lists-action-button lists-return-button" type="button" @click="clearActiveWordListGroup">
            <ArrowLeft :size="16" aria-hidden="true" />
            <span>返回未归组</span>
          </button>
        </div>
        <form v-if="activeGroup" class="word-list-group-delete-form" @submit.prevent="deleteActiveWordListGroup">
          <label>
            <span class="sr-only">删除单词组密码</span>
            <input
              v-model="groupDeletePassword"
              type="password"
              placeholder="输入密码删除"
              autocomplete="current-password"
            >
          </label>
          <button
            class="word-list-group-delete-button"
            type="submit"
            :disabled="!trimmedGroupDeletePassword || isDeletingGroup"
          >
            <Trash2 :size="15" aria-hidden="true" />
            <span>{{ isDeletingGroup ? "删除中" : "删除单词组" }}</span>
          </button>
          <span v-if="groupDeleteNotice" class="word-list-group-delete-notice">{{ groupDeleteNotice }}</span>
        </form>
      </div>
    </div>
    <section v-if="displayedCards.length" class="word-grid lists-reorder-grid" role="list" @dragover.prevent>
      <WordListCard
        v-for="(card, index) in displayedCards"
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
    <p v-else class="empty-state list-group-empty list-table-empty">
      {{ activeGroup ? "这个单词组里还没有单词表。" : "没有未归组的单词表。" }}
    </p>
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

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
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
  gap: 18px;
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
  inset: 0 auto 0 0;
  width: 5px;
  border-radius: 18px 0 0 18px;
  background: linear-gradient(180deg, #0f7f59, rgba(243, 190, 95, 0.76), rgba(15, 127, 89, 0.18));
}

.lists-section-head {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: start;
  gap: 18px;
  min-height: 104px;
  border: 1px solid rgba(15, 127, 89, 0.13);
  border-radius: 16px;
  padding: 20px 22px 18px 28px;
  background:
    radial-gradient(circle at 92% 16%, rgba(243, 190, 95, 0.13), transparent 30%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(239, 250, 245, 0.94));
  box-shadow: 0 12px 28px rgba(15, 28, 36, 0.05);
}

.lists-section-head::before {
  content: "";
  position: absolute;
  top: 20px;
  bottom: 20px;
  left: 14px;
  width: 4px;
  border-radius: 999px;
  background: linear-gradient(180deg, #0f7f59, rgba(243, 190, 95, 0.72));
}

.lists-section-head h2 {
  margin: 0;
  color: #111827;
  font-size: clamp(22px, 3vw, 30px);
  line-height: 1.1;
}

.lists-section-copy {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.lists-section-copy > span {
  max-width: 520px;
  color: #5c6f7e;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.45;
}

.lists-section-meta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 190px;
  border: 1px solid rgba(15, 127, 89, 0.14);
  border-radius: 18px;
  padding: 10px 12px;
  color: #0f6b4d;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 10px 24px rgba(15, 28, 36, 0.05);
  white-space: nowrap;
}

.lists-section-meta strong {
  color: #0f7f59;
  font-size: 24px;
  line-height: 1;
  font-weight: 1000;
}

.lists-section-meta span {
  color: #496073;
  font-size: 12px;
  font-weight: 900;
}

.word-list-groups-head > .lists-action-button,
.lists-table-actions {
  justify-self: end;
}

.lists-table-actions {
  display: grid;
  align-self: start;
  gap: 8px;
}

.lists-table-actions-row {
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  gap: 12px;
}

.lists-return-button {
  min-height: 44px;
  border: 0;
  border-radius: 14px;
  padding: 0 18px;
  color: #fff;
  background: linear-gradient(135deg, #0f7f59, #0a6145);
  box-shadow: 0 14px 30px rgba(15, 127, 89, 0.24);
  font-size: 14px;
  font-weight: 1000;
  white-space: nowrap;
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
}

.lists-return-button:hover,
.lists-return-button:focus-visible {
  color: #fff;
  background: linear-gradient(135deg, #0b6f4c, #074c36);
  box-shadow: 0 18px 36px rgba(15, 127, 89, 0.3);
  transform: translateY(-1px);
}

.lists-return-button:focus-visible {
  outline: 3px solid rgba(15, 127, 89, 0.22);
  outline-offset: 3px;
}

.word-list-group-delete-form {
  display: grid;
  grid-template-columns: minmax(150px, 190px) auto;
  align-items: center;
  justify-self: end;
  gap: 8px;
  max-width: 100%;
}

.word-list-group-delete-form label {
  min-width: 0;
}

.word-list-group-delete-form input {
  width: 100%;
  min-height: 40px;
  border: 1px solid rgba(185, 28, 28, 0.18);
  border-radius: 12px;
  padding: 0 12px;
  color: #7f1d1d;
  background: rgba(255, 255, 255, 0.92);
  font: inherit;
  font-size: 13px;
  font-weight: 900;
  box-shadow: 0 10px 22px rgba(127, 29, 29, 0.04);
}

.word-list-group-delete-form input:focus {
  border-color: rgba(185, 28, 28, 0.45);
  outline: 3px solid rgba(185, 28, 28, 0.1);
}

.word-list-group-delete-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 40px;
  border: 0;
  border-radius: 12px;
  padding: 0 14px;
  color: #fff;
  background: linear-gradient(135deg, #b91c1c, #8f1616);
  box-shadow: 0 12px 24px rgba(185, 28, 28, 0.2);
  font: inherit;
  font-size: 13px;
  font-weight: 1000;
  white-space: nowrap;
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease, opacity 0.16s ease;
}

.word-list-group-delete-button:hover,
.word-list-group-delete-button:focus-visible {
  color: #fff;
  box-shadow: 0 16px 30px rgba(185, 28, 28, 0.27);
  transform: translateY(-1px);
}

.word-list-group-delete-button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
  transform: none;
}

.word-list-group-delete-notice {
  grid-column: 1 / -1;
  color: #b42318;
  font-size: 12px;
  font-weight: 900;
  text-align: right;
}

.word-list-group-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  padding: 0;
}

.word-list-group-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: start;
  min-height: 136px;
  border: 1px solid rgba(15, 127, 89, 0.18);
  border-radius: 20px;
  padding: 18px;
  color: #0f172a;
  background:
    radial-gradient(circle at 100% 0%, rgba(243, 190, 95, 0.15), transparent 32%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.99), rgba(229, 246, 238, 0.92));
  box-shadow: 0 18px 36px rgba(15, 28, 36, 0.08);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: transform 0.16s ease, border-color 0.16s ease, background 0.16s ease, color 0.16s ease, box-shadow 0.16s ease;
}

.word-list-group-card::before {
  content: "";
  position: absolute;
  top: -1px;
  left: 22px;
  width: 86px;
  height: 15px;
  border: 1px solid rgba(15, 127, 89, 0.16);
  border-bottom: 0;
  border-radius: 15px 15px 0 0;
  background: rgba(232, 247, 239, 0.98);
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
  background:
    radial-gradient(circle at 86% 16%, rgba(255, 255, 255, 0.18), transparent 26%),
    linear-gradient(135deg, #0f7f59, #0b5f43);
  transform: translateY(-1px);
  box-shadow: 0 24px 48px rgba(15, 127, 89, 0.2);
}

.word-list-group-card.is-active,
.word-list-group-card.is-drop-target {
  border-color: rgba(15, 127, 89, 0.72);
  background:
    radial-gradient(circle at 86% 16%, rgba(255, 255, 255, 0.16), transparent 26%),
    linear-gradient(135deg, #0f7f59, #0b5f43);
  color: #fff;
  box-shadow: 0 18px 36px rgba(15, 127, 89, 0.2);
}

.word-list-group-card.is-drop-target {
  outline: 3px solid rgba(243, 190, 95, 0.48);
  outline-offset: 4px;
}

.word-list-group-card:hover strong,
.word-list-group-card:hover span,
.word-list-group-card:hover div span,
.word-list-group-card.is-active strong,
.word-list-group-card.is-active span,
.word-list-group-card.is-active div span,
.word-list-group-card.is-drop-target strong,
.word-list-group-card.is-drop-target span,
.word-list-group-card.is-drop-target div span {
  color: #fff;
}

.word-list-group-card:hover::before,
.word-list-group-card.is-active::before,
.word-list-group-card.is-drop-target::before {
  border-color: rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.14);
}

.word-list-group-card:hover::after,
.word-list-group-card.is-active::after,
.word-list-group-card.is-drop-target::after {
  background: rgba(255, 255, 255, 0.14);
}

.word-list-group-index {
  position: relative;
  z-index: 1;
  display: inline-grid;
  grid-column: 1 / -1;
  place-items: center;
  width: fit-content;
  min-width: 44px;
  min-height: 30px;
  border-radius: 999px;
  padding: 6px 10px;
  color: #0f6b4d;
  background: rgba(232, 247, 239, 0.96);
  font-size: 15px;
  font-weight: 1000;
}

.word-list-group-card:hover .word-list-group-index,
.word-list-group-card.is-active .word-list-group-index,
.word-list-group-card.is-drop-target .word-list-group-index {
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
}

.word-list-group-card div {
  display: grid;
  grid-column: 1 / -1;
  gap: 7px;
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

.word-list-group-action {
  grid-column: 1 / -1;
  justify-self: start;
  align-self: center;
  border: 1px solid rgba(15, 127, 89, 0.12);
  border-radius: 999px;
  padding: 6px 9px;
  color: #0f6b4d;
  background: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  font-weight: 950;
  white-space: nowrap;
}

.word-list-group-card:hover .word-list-group-action,
.word-list-group-card.is-active .word-list-group-action,
.word-list-group-card.is-drop-target .word-list-group-action {
  border-color: rgba(255, 255, 255, 0.24);
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
}

.list-group-empty {
  display: grid;
  place-items: center;
  min-height: 84px;
  margin: 0 18px 18px;
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
  overflow: hidden;
  padding: 18px;
  border-color: rgba(15, 127, 89, 0.13);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(249, 253, 250, 0.92));
  box-shadow: 0 16px 40px rgba(15, 28, 36, 0.06);
}

.lists-table-head {
  grid-template-columns: minmax(0, 1fr) auto;
  margin: 0;
}

.lists-table-head::after {
  content: "";
  position: absolute;
  inset: auto 22px 0 24px;
  height: 3px;
  border-radius: 999px 999px 0 0;
  background: linear-gradient(90deg, rgba(15, 127, 89, 0.58), rgba(96, 165, 250, 0.28), transparent);
}

.word-list-table-panel .lists-reorder-grid {
  padding: 0;
}

.list-table-empty {
  margin-top: 0;
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
  gap: 16px;
}

.list-group-create-form label,
.list-group-manage-form label {
  display: grid;
  gap: 8px;
  color: #536579;
  font-size: 13px;
  font-weight: 900;
}

.list-group-create-form input,
.list-group-manage-form select {
  min-height: 48px;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 0 14px;
  color: var(--text);
  background: rgba(255, 255, 255, 0.94);
  font: inherit;
  font-weight: 850;
  box-shadow: 0 10px 22px rgba(15, 28, 36, 0.04);
}

.list-group-create-form input:focus,
.list-group-manage-form select:focus {
  border-color: rgba(15, 127, 89, 0.55);
  outline: 3px solid rgba(15, 127, 89, 0.12);
}

.list-group-create-submit {
  justify-content: center;
  min-height: 48px;
  border-radius: 14px;
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
    grid-template-columns: 1fr;
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

  .lists-section-meta {
    justify-content: flex-start;
    min-width: 0;
    width: 100%;
  }

  .lists-table-actions,
  .lists-table-actions-row {
    align-items: stretch;
    width: 100%;
  }

  .lists-table-actions-row {
    flex-direction: column;
  }

  .lists-table-actions .lists-return-button {
    width: 100%;
  }

  .word-list-group-delete-form {
    grid-column: 1;
    grid-template-columns: 1fr;
    justify-self: stretch;
  }

  .word-list-group-delete-button {
    width: 100%;
  }

  .word-list-group-delete-notice {
    text-align: left;
  }

  .list-word-search-form {
    grid-template-columns: 1fr;
  }

  .word-list-group-grid {
    grid-template-columns: 1fr;
  }
}
</style>
