<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

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

const INDIVIDUAL_COLLECTION_KEY = "individual";
const SPB_SYNC_STORAGE_KEY = "speakeasy:spb-sync-jobs:v1";
const ACTIVE_SYNC_STATUSES = new Set(["queued", "running"]);
const activeKey = ref("");
const pageData = ref(props.data);
const syncingKey = ref("");
const syncNotice = ref("");
const syncJob = ref(null);
let syncPollTimer = null;

const collections = computed(() => pageData.value.collections || []);
const activeCollection = computed(
  () =>
    pageData.value.collection ||
    collections.value.find((collection) => collection.key === INDIVIDUAL_COLLECTION_KEY) ||
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
const activeSyncJob = computed(() => {
  if (!syncJob.value || syncJob.value.key !== activeGroup.value?.key) return null;
  return syncJob.value;
});
const syncProgressPercent = computed(() => {
  const job = activeSyncJob.value;
  if (!job) return 0;
  if (job.status === "complete") return 100;
  if (job.stage === "importing") return 96;
  const total = Number(job.total || 0);
  const processed = Number(job.processed || 0);
  return total > 0 ? Math.max(4, Math.min(95, Math.round((processed / total) * 100))) : 4;
});
const syncProgressLabel = computed(() => {
  const job = activeSyncJob.value;
  if (!job) return "";
  const total = Number(job.total || 0);
  const processed = Number(job.processed || 0);
  if (job.status === "complete") return "100%";
  if (job.stage === "importing") return "写入中";
  return total > 0 ? `${processed} / ${total}` : "排队中";
});

watch(
  () => props.data,
  (nextData) => {
    pageData.value = nextData;
    resumeSyncJobFromPayload(nextData);
  },
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
  if (group.source_url_configured) return `公开源可导入 ${group.source_count || 0} 个单词`;
  if (group.cached_source_count) return `缓存可导入 ${group.cached_source_count} 个单词`;
  if (group.sync_ready) return "可从小程序接口同步";
  return "等待获取词库";
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

function clearSyncPoll() {
  if (syncPollTimer) {
    window.clearTimeout(syncPollTimer);
    syncPollTimer = null;
  }
}

function readStoredSyncJobs() {
  try {
    return JSON.parse(window.localStorage.getItem(SPB_SYNC_STORAGE_KEY) || "{}") || {};
  } catch {
    return {};
  }
}

function writeStoredSyncJobs(jobs) {
  try {
    window.localStorage.setItem(SPB_SYNC_STORAGE_KEY, JSON.stringify(jobs));
  } catch {
    // Local storage can be unavailable in private windows; polling still works in-page.
  }
}

function rememberSyncJob(job) {
  if (!job?.id || !ACTIVE_SYNC_STATUSES.has(job.status)) return;
  const collectionKey = job.collection || activeCollection.value?.key || INDIVIDUAL_COLLECTION_KEY;
  const jobs = readStoredSyncJobs();
  jobs[collectionKey] = {
    id: job.id,
    collection: collectionKey,
    key: job.key || activeKey.value,
  };
  writeStoredSyncJobs(jobs);
}

function forgetStoredSyncJob(collectionKey) {
  const key = collectionKey || activeCollection.value?.key || INDIVIDUAL_COLLECTION_KEY;
  const jobs = readStoredSyncJobs();
  if (!jobs[key]) return;
  delete jobs[key];
  writeStoredSyncJobs(jobs);
}

function applyRunningSyncJob(job, notice = "") {
  if (!job?.id || !ACTIVE_SYNC_STATUSES.has(job.status)) return false;
  syncJob.value = job;
  syncingKey.value = job.key || "";
  if (job.key) activeKey.value = job.key;
  syncNotice.value = notice || job.message || "正在恢复同步进度...";
  rememberSyncJob(job);
  pollSyncJob(job.id, job.key || activeKey.value);
  return true;
}

function resumeSyncJobFromPayload(payload) {
  const job = payload?.active_sync_job;
  if (!job || syncJob.value?.id === job.id) return false;
  return applyRunningSyncJob(job);
}

function resumeStoredSyncJob() {
  const collectionKey = activeCollection.value?.key || INDIVIDUAL_COLLECTION_KEY;
  const storedJob = readStoredSyncJobs()[collectionKey];
  if (!storedJob?.id || syncJob.value?.id === storedJob.id) return false;
  return applyRunningSyncJob(
    {
      id: storedJob.id,
      collection: collectionKey,
      key: storedJob.key || activeKey.value,
      status: "queued",
      stage: "queued",
      total: 0,
      processed: 0,
      message: "正在恢复同步进度...",
    },
    "正在恢复同步进度...",
  );
}

async function pollSyncJob(jobId, groupKey) {
  clearSyncPoll();
  try {
    const payload = await fetchJson(routeApiPaths.spbSyncStatus(jobId), { skipCache: true });
    if (payload.job) {
      syncJob.value = payload.job;
      if (ACTIVE_SYNC_STATUSES.has(payload.job.status)) {
        syncingKey.value = payload.job.key || groupKey;
        rememberSyncJob(payload.job);
      }
    }
    if (payload.collection) {
      pageData.value = payload;
      activeKey.value = payload.job?.key || groupKey;
    }
    const status = payload.job?.status;
    if (status === "complete") {
      syncingKey.value = "";
      forgetStoredSyncJob(payload.job?.collection);
      syncNotice.value = payload.message || "词库已同步。";
      return;
    }
    if (status === "failed") {
      syncingKey.value = "";
      forgetStoredSyncJob(payload.job?.collection);
      syncNotice.value = payload.message || "同步失败，请稍后再试。";
      return;
    }
    syncPollTimer = window.setTimeout(() => pollSyncJob(jobId, groupKey), 1200);
  } catch (error) {
    if ((error.message || "").includes("不存在") || (error.message || "").includes("已过期")) {
      forgetStoredSyncJob(activeCollection.value?.key);
    }
    syncingKey.value = "";
    syncNotice.value = error.message || "同步状态获取失败，请稍后再试。";
  }
}

async function syncGroup(group) {
  if (!canSyncGroup(group) || syncingKey.value) return;
  clearSyncPoll();
  syncingKey.value = group.key;
  syncJob.value = null;
  syncNotice.value = group.sync_ready || group.cached_source_count ? "" : group.sync_note || "";
  const isDetailUpdate = Number(group.total_count || 0) > 0;
  try {
    const payload = await fetchJson(isDetailUpdate ? routeApiPaths.spbBackfillDetails() : routeApiPaths.spbSync(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collection: activeCollection.value.key || INDIVIDUAL_COLLECTION_KEY, key: group.key }),
      skipCache: true,
    });
    if (payload.collection) pageData.value = payload;
    activeKey.value = group.key;
    if (payload.job) {
      syncJob.value = payload.job;
      rememberSyncJob(payload.job);
      syncNotice.value = payload.message || "同步任务已开始。";
      pollSyncJob(payload.job.id, group.key);
      return;
    }
    syncNotice.value = payload.message || "词库已同步。";
    syncingKey.value = "";
  } catch (error) {
    syncNotice.value = error.message || "同步失败，请稍后再试。";
    syncingKey.value = "";
  }
}

onMounted(() => {
  if (!resumeSyncJobFromPayload(pageData.value)) resumeStoredSyncJob();
});

onBeforeUnmount(clearSyncPoll);

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

      <div
        v-if="activeSyncJob"
        class="spb-sync-progress"
        :class="{ 'is-syncing': activeSyncJob.status === 'queued' || activeSyncJob.status === 'running', 'has-error': activeSyncJob.status === 'failed', 'is-complete': activeSyncJob.status === 'complete' }"
      >
        <div class="spb-sync-progress-meta">
          <span>{{ activeSyncJob.message || "正在同步词库..." }}</span>
          <strong>{{ syncProgressLabel }}</strong>
        </div>
        <div class="sync-progress" aria-label="SPB 同步进度">
          <span :style="{ width: `${syncProgressPercent}%` }"></span>
        </div>
        <p v-if="activeSyncJob.current_word" class="spb-sync-progress-current">
          当前处理：{{ activeSyncJob.current_word }}
        </p>
      </div>

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
