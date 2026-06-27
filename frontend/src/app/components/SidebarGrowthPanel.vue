<script setup>
import { computed } from "vue";

const props = defineProps({
  growth: {
    type: Object,
    default: null,
  },
  navigate: {
    type: Function,
    required: true,
  },
});

const metrics = computed(() => props.growth?.metrics?.slice(0, 3) || []);
const trophyImage = computed(() => props.growth?.trophyImageUrl || "/static/icons/challenge-crown-transparent.png");

function openHome() {
  props.navigate("/");
}
</script>

<template>
  <section class="sidebar-growth-panel" aria-label="成长成就">
    <button type="button" class="sidebar-growth-head" @click="openHome">
      <img :src="trophyImage" alt="" aria-hidden="true" />
      <span>
        <small>成长等级</small>
        <strong>Lv. {{ growth?.level || 1 }}</strong>
      </span>
      <em>{{ growth?.points || 0 }} 分</em>
    </button>
    <div v-if="metrics.length" class="sidebar-growth-metrics">
      <div v-for="item in metrics" :key="item.key" class="sidebar-growth-metric">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}/{{ item.target }}</strong>
        <i><b :style="{ width: `${item.percent || 0}%` }"></b></i>
      </div>
    </div>
  </section>
</template>
