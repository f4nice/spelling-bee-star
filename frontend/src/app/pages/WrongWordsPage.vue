<script setup>
import { computed, ref } from "vue";
import WrongWordGroupCard from "../components/WrongWordGroupCard.vue";

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

const activeFilter = ref("pending");

const groups = computed(() => props.data?.groups || []);

const counts = computed(() => {
  const fallback = groups.value.reduce(
    (total, group) => {
      total.pending += Number(group.pending_count ?? group.count ?? 0);
      total.corrected += Number(group.corrected_count || 0);
      return total;
    },
    { pending: 0, corrected: 0 },
  );
  return {
    pending: Number(props.data?.counts?.pending ?? fallback.pending),
    corrected: Number(props.data?.counts?.corrected ?? fallback.corrected),
  };
});

const filterOptions = computed(() => [
  { key: "pending", label: "未纠正", count: counts.value.pending },
  { key: "corrected", label: "已纠正", count: counts.value.corrected },
]);

const filteredGroups = computed(() => {
  if (activeFilter.value === "corrected") {
    return groups.value.filter((group) => Number(group.corrected_count || 0) > 0);
  }
  return groups.value.filter((group) => Number(group.pending_count ?? group.count ?? 0) > 0);
});

const emptyText = computed(() => (activeFilter.value === "corrected" ? "还没有已经纠正的生词。" : "没有待纠正的生词。"));
</script>

<template>
  <section class="panel word-resource-filter-panel wrong-words-filter-panel">
    <div class="word-resource-filter-top">
      <div>
        <strong>生词筛选</strong>
        <span>当前 {{ filteredGroups.length }} 个日期</span>
      </div>
      <div class="word-resource-filter-actions" role="group" aria-label="生词本筛选">
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
  </section>

  <section class="word-grid">
    <WrongWordGroupCard
      v-for="group in filteredGroups"
      :key="group.date"
      :group="group"
      :go="go"
    />
    <div v-if="!filteredGroups.length" class="empty-state">{{ emptyText }}</div>
  </section>
</template>
