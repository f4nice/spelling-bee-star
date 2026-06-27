<script setup>
import { computed } from "vue";

const props = defineProps({
  growth: {
    type: Object,
    default: null,
  },
});

const metrics = computed(() => props.growth?.metrics || []);
const missions = computed(() => props.growth?.dailyMissions || []);
const trophyImage = computed(() => props.growth?.trophyImageUrl || "/static/icons/challenge-crown-transparent.png");

function badgeLabel(item) {
  return item.badgeLabel || item.badge_label || item.label;
}
</script>

<template>
  <section v-if="growth" class="home-growth-console" aria-label="成长成就">
    <div class="home-growth-main">
      <img :src="trophyImage" alt="" aria-hidden="true" />
      <div>
        <p class="section-kicker">ACHIEVEMENT</p>
        <h3>{{ growth.title || "成长成就" }}</h3>
        <p>{{ growth.subtitle || "每天完成挑战，点亮自己的奖杯墙" }}</p>
      </div>
      <strong>Lv. {{ growth.level || 1 }}</strong>
    </div>

    <div v-if="metrics.length" class="home-growth-badges">
      <article
        v-for="item in metrics"
        :key="item.key"
        class="growth-badge-card"
        :class="`tier-${item.tier || 'gold'}`"
      >
        <div class="growth-badge-medal">
          <img :src="item.iconUrl || trophyImage" alt="" aria-hidden="true" />
        </div>
        <div>
          <strong>{{ badgeLabel(item) }}</strong>
          <span>{{ item.label }} {{ item.value }}/{{ item.target }}{{ item.unit || "" }}</span>
          <i><b :style="{ width: `${item.percent || 0}%` }"></b></i>
        </div>
      </article>
    </div>

    <div v-if="missions.length" class="home-growth-missions">
      <span v-for="mission in missions" :key="mission.key">
        {{ mission.label }} {{ mission.value }}/{{ mission.target }}
      </span>
    </div>
  </section>
</template>
