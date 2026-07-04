<script setup>
import { computed, ref, watch } from "vue";

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

const activeKey = ref("");

const groups = computed(() => props.data.groups || []);
const syncedGroups = computed(() => groups.value.filter((group) => group.total_count > 0));
const activeGroup = computed(
  () => groups.value.find((group) => group.key === activeKey.value) || syncedGroups.value[0] || groups.value[0],
);
const collection = computed(() => props.data.collection || {});
const totalSyncedWords = computed(() => syncedGroups.value.reduce((total, group) => total + Number(group.total_count || 0), 0));
const totalSyncedLists = computed(() => syncedGroups.value.reduce((total, group) => total + Number(group.list_count || 0), 0));

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
  if (group.source_count) return `缓存可见 ${group.source_count} 个单词`;
  return "等待获取词库";
}

function openGroup(group) {
  activeKey.value = group.key;
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
</script>

<template>
  <section class="spb-page">
    <section class="panel app-page-heading spb-heading">
      <div class="page-heading-title">
        <p class="section-kicker">SPB</p>
        <h1>{{ collection.name || "个人赛冠军词库" }}</h1>
        <p>{{ collection.subtitle || "Champion Word Bank for Individual Competitions" }}</p>
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

    <section v-if="activeGroup" class="panel spb-group-panel">
      <header class="spb-group-head">
        <div>
          <p class="section-kicker">Word Bank</p>
          <h2>{{ activeGroup.title }}</h2>
          <span>{{ activeGroup.subtitle }}</span>
        </div>
        <strong>{{ groupStatusLabel(activeGroup) }}</strong>
      </header>

      <div v-if="activeGroup.cards?.length" class="spb-list-grid">
        <article v-for="card in activeGroup.cards" :key="card.list.id" class="spb-list-card">
          <button class="plain-card-button spb-list-main" type="button" @click="openList(card)">
            <span>{{ card.list.name }}</span>
            <strong>{{ card.count }} 个单词</strong>
            <small v-if="challengeRemain(card) > 0">剩余 {{ challengeRemain(card) }} 个</small>
            <small v-else>可复习</small>
          </button>
          <button class="secondary-button" type="button" @click="openList(card)">查看</button>
          <button class="primary-action-button" type="button" @click="openChallenge(card)">挑战</button>
        </article>
      </div>

      <div v-else class="spb-empty-panel">
        <strong>{{ activeGroup.status === "locked" ? "这组在小程序里还未解锁" : "这组还没有同步到 SpeakEasy" }}</strong>
        <span>{{ activeGroup.source_count ? `已能读取到 ${activeGroup.source_count} 个源词，待导入后会在这里出现。` : "获取到词库后会按 500 个单词自动拆分成多个单词表。" }}</span>
      </div>
    </section>
  </section>
</template>
