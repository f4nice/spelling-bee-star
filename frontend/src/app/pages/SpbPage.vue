<script setup>
import { computed, ref, watch } from "vue";

import { routeApiPaths } from "../routeApiPaths.js";
import { fetchJson } from "../utils.js";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});

const activeCollectionKey = ref("");
const activeKey = ref("");
const pageData = ref(props.data);
const syncingKey = ref("");
const backfillingKey = ref("");
const syncNotice = ref("");

const collections = computed(() => pageData.value.collections || []);
const activeCollection = computed(
  () =>
    collections.value.find((collection) => collection.key === activeCollectionKey.value) ||
    pageData.value.collection ||
    collections.value[0] ||
    {},
);
const groups = computed(() => activeCollection.value.groups || pageData.value.groups || []);
const syncedGroups = computed(() => groups.value.filter((group) => group.total_count > 0));
const activeGroup = computed(
  () => groups.value.find((group) => group.key === activeKey.value) || syncedGroups.value[0] || groups.value[0],
);
const totalSyncedWords = computed(() => syncedGroups.value.reduce((total, group) => total + Number(group.total_count || 0), 0));
const totalSyncedLists = computed(() => syncedGroups.value.reduce((total, group) => total + Number(group.list_count || 0), 0));

watch(
  () => props.data,
  (nextData) => {
    pageData.value = nextData;
  },
);

watch(
  collections,
  (nextCollections) => {
    if (nextCollections.some((collection) => collection.key === activeCollectionKey.value)) return;
    activeCollectionKey.value = pageData.value.collection?.key || nextCollections[0]?.key || "individual";
  },
  { immediate: true },
);

watch(
  groups,
  (nextGroups) => {
    if (nextGroups.some((group) => group.key === activeKey.value)) return;
    activeKey.value = nextGroups.find((group) => group.total_count > 0)?.key || nextGroups[0]?.key || "";
  },
  { immediate: true },
);

function groupStatusLabel(group) {
  if (group.total_count > 0) return "已同步";
  if (group.status === "locked") return "小程序锁定";
  return "待同步";
}

function groupMeta(group) {
  if (group.total_count > 0) return `${group.total_count} 个单词 · ${group.list_count} 个分表`;
  if (group.cached_source_count) return `缓存可导入 ${group.cached_source_count} 个单词`;
  if (group.sync_ready) return "可从小程序接口同步";
  return "等待获取词库";
}

function collectionStatusLabel(collection) {
  if (collection.total_count > 0) return "已同步";
  if (collection.cached_source_count > 0) return "有缓存";
  return "待获取";
}

function collectionMeta(collection) {
  if (collection.total_count > 0) return `${collection.total_count} 个单词 · ${collection.list_count} 个分表`;
  if (collection.cached_source_count > 0) return `缓存可导入 ${collection.cached_source_count} 个`;
  return collection.sync_note || "等待获取词库";
}

function openCollection(collection) {
  activeCollectionKey.value = collection.key;
  activeKey.value = collection.groups?.find((group) => group.total_count > 0)?.key || collection.groups?.[0]?.key || "";
  syncNotice.value = "";
}

function openGroup(group) {
  activeKey.value = group.key;
  syncNotice.value = "";
}

function openList(card) {
  if (card?.list?.id) props.go(`/lists/${card.list.id}`);
}

function openChallenge(card) {
  if (card?.list?.id) props.go(`/challenge/${card.list.id}`);
}

function challengeRemain(card) {
  const challenge = card?.challenge || {};
  return Number(challenge.remaining_count ?? challenge.remaining ?? 0);
}

function canSyncGroup(group) {
  return Boolean(group && group.status !== "locked" && (group.total_count || group.sync_ready || group.cached_source_count));
}

function syncButtonText(group) {
  if (syncingKey.value === group?.key) return "同步中...";
  if (group?.total_count) return "更新详情";
  if (group?.sync_ready) return "同步词库";
  if (group?.cached_source_count) return "导入缓存";
  return "检查同步";
}

function canBackfillGroup(group) {
  return Boolean(group?.total_count && Number(group.missing_detail_count || 0) > 0);
}

function backfillButtonText(group) {
  if (backfillingKey.value === group?.key) return "补全中...";
  const count = Number(group?.missing_detail_count || 0);
  return count > 0 ? `补全缺失 ${count}` : "补全缺失";
}

async function syncGroup(group) {
  if (!canSyncGroup(group) || syncingKey.value) return;
  syncingKey.value = group.key;
  syncNotice.value = group.sync_ready || group.cached_source_count ? "" : group.sync_note || "";
  try {
    const payload = await fetchJson(routeApiPaths.spbSync(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collection: activeCollection.value.key || "individual", key: group.key }),
      skipCache: true,
    });
    pageData.value = payload;
    activeCollectionKey.value = payload.collection?.key || activeCollectionKey.value;
    activeKey.value = group.key;
    syncNotice.value = payload.message || "词库已同步。";
  } catch (error) {
    syncNotice.value = error.message || "同步失败，请稍后再试。";
  } finally {
    syncingKey.value = "";
  }
}

async function backfillGroup(group) {
  if (!canBackfillGroup(group) || backfillingKey.value) return;
  backfillingKey.value = group.key;
  syncNotice.value = "";
  try {
    const payload = await fetchJson(routeApiPaths.spbBackfillDetails(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collection: activeCollection.value.key || "individual", key: group.key }),
      skipCache: true,
    });
    pageData.value = payload;
    activeCollectionKey.value = payload.collection?.key || activeCollectionKey.value;
    activeKey.value = group.key;
    syncNotice.value = payload.message || "已开始补全缺失的音标、词性、英文定义和英文例句。";
  } catch (error) {
    syncNotice.value = error.message || "补全失败，请稍后再试。";
  } finally {
    backfillingKey.value = "";
  }
}
</script>

<template>
  <section class="spb-page">
    <section class="panel app-page-heading spb-heading">
      <div class="page-heading-title">
        <p class="section-kicker">SPB</p>
        <h1>{{ activeCollection.name || "个人赛冠军词库" }}</h1>
        <p>{{ activeCollection.subtitle || "Champion Word Bank for Individual Competitions" }}</p>
      </div>
      <div class="spb-heading-stats" aria-label="SPB 词库同步状态">
        <span>
          <strong>{{ totalSyncedWords }}</strong>
          已同步单词
        </span>
        <span>
          <strong>{{ totalSyncedLists }}</strong>
          分表
        </span>
      </div>
    </section>

    <section class="panel spb-collection-panel">
      <div class="spb-collection-hero">
        <div>
          <p class="section-kicker">WORD LIBRARY</p>
          <h2>SPB 词库中心</h2>
          <span>{{ activeCollection.name || "个人赛冠军词库" }}</span>
        </div>
        <div class="spb-hero-picture" aria-hidden="true">
          <div class="spb-hero-book">
            <span>S</span>
            <span>P</span>
            <span>B</span>
          </div>
          <div class="spb-hero-ribbon"></div>
          <div class="spb-hero-lines">
            <i></i>
            <i></i>
            <i></i>
          </div>
        </div>
      </div>

      <section class="spb-collection-grid" aria-label="SPB 词库分类">
        <button
          v-for="collectionItem in collections"
          :key="collectionItem.key"
          class="spb-collection-card"
          :class="{ active: activeCollection?.key === collectionItem.key, synced: collectionItem.total_count > 0 }"
          type="button"
          @click="openCollection(collectionItem)"
        >
          <span>{{ collectionStatusLabel(collectionItem) }}</span>
          <strong>{{ collectionItem.name }}</strong>
          <small>{{ collectionMeta(collectionItem) }}</small>
        </button>
      </section>
    </section>

    <section v-if="groups.length" class="panel spb-category-panel">
      <header class="spb-category-head">
        <div>
          <p class="section-kicker">CATEGORY</p>
          <h2>{{ activeCollection.name || "个人赛冠军词库" }}</h2>
          <span>{{ activeCollection.subtitle || "Champion Word Bank for Individual Competitions" }}</span>
        </div>
        <strong>{{ groups.length }} 个组别</strong>
      </header>

      <section class="spb-bank-grid" aria-label="SPB 词库组别">
        <button
          v-for="group in groups"
          :key="group.key"
          class="spb-bank-card"
          :class="{ active: activeGroup?.key === group.key, synced: group.total_count > 0, locked: group.status === 'locked' && !group.total_count }"
          type="button"
          @click="openGroup(group)"
        >
          <span class="spb-bank-status">{{ groupStatusLabel(group) }}</span>
          <strong>{{ group.title }}</strong>
          <em>{{ group.subtitle }}</em>
          <small>{{ groupMeta(group) }}</small>
        </button>
      </section>
    </section>

    <section v-if="activeGroup" class="panel spb-group-panel">
      <header class="spb-group-head">
        <div>
          <p class="section-kicker">Word Bank</p>
          <h2>{{ activeGroup.title }}</h2>
          <span>{{ activeGroup.subtitle }}</span>
        </div>
        <div class="spb-group-actions">
          <button
            v-if="canBackfillGroup(activeGroup)"
            class="secondary-button compact-button"
            type="button"
            :disabled="backfillingKey === activeGroup.key"
            @click="backfillGroup(activeGroup)"
          >
            {{ backfillButtonText(activeGroup) }}
          </button>
          <button
            v-if="canSyncGroup(activeGroup)"
            class="primary-action-button"
            type="button"
            :disabled="syncingKey === activeGroup.key"
            @click="syncGroup(activeGroup)"
          >
            {{ syncButtonText(activeGroup) }}
          </button>
          <strong>{{ groupStatusLabel(activeGroup) }}</strong>
        </div>
      </header>

      <p v-if="syncNotice || activeGroup.sync_note" class="notice spb-sync-notice">
        {{ syncNotice || activeGroup.sync_note }}
      </p>

      <div v-if="activeGroup.cards?.length" class="spb-list-grid">
        <article v-for="card in activeGroup.cards" :key="card.list.id" class="spb-list-card">
          <button class="plain-card-button spb-list-main" type="button" @click="openList(card)">
            <span>{{ card.list.name }}</span>
            <small v-if="challengeRemain(card) > 0">剩余 {{ challengeRemain(card) }} 个待挑战</small>
            <small v-else>可复习</small>
          </button>
          <div class="spb-list-count">
            <strong>{{ card.count }}</strong>
            <span>个单词</span>
          </div>
          <div class="spb-list-actions">
            <button class="secondary-button compact-button" type="button" @click="openList(card)">查看</button>
            <button class="primary-action-button compact-button" type="button" @click="openChallenge(card)">挑战</button>
          </div>
        </article>
      </div>

      <div v-else class="spb-empty-panel">
        <strong>{{ activeGroup.status === "locked" ? "这组在小程序里还未解锁" : "这组还没有同步到 SpeakEasy" }}</strong>
        <span>{{ activeGroup.source_count ? `已能读取到 ${activeGroup.source_count} 个源词，待导入后会在这里出现。` : activeGroup.sync_note || "获取到词库后会按 500 个单词自动拆分成多个单词表。" }}</span>
      </div>
    </section>

    <section v-else class="panel spb-group-panel">
      <div class="spb-empty-panel">
        <strong>{{ activeCollection.name || "这个分类" }} 暂时没有可同步词库</strong>
        <span>{{ activeCollection.sync_note || "等小程序接口返回词库或服务器放入缓存后，这里会自动出现可同步分表。" }}</span>
      </div>
    </section>
  </section>
</template>
