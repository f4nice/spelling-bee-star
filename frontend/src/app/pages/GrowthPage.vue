<script setup>
import { computed } from "vue";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
});

const growth = computed(() => props.data.growth || {});
const metrics = computed(() => growth.value.metrics || []);
const missions = computed(() => growth.value.dailyMissions || []);
const trophyImage = computed(() => growth.value.trophyImageUrl || "/static/icons/challenge-crown-transparent.png");
const levelProgress = computed(() => growth.value.levelProgressPercent ?? 0);
const nextLevelPoints = computed(() => growth.value.nextLevelPoints ?? (growth.value.level || 1) * 500);
const pointsToNextLevel = computed(() => growth.value.pointsToNextLevel ?? Math.max(nextLevelPoints.value - (growth.value.points || 0), 0));
const rules = computed(() => growth.value.scoreRules || []);

function badgeLabel(item) {
  return item.badgeLabel || item.badge_label || item.label;
}
</script>

<template>
  <section class="growth-detail-page">
    <div class="growth-detail-hero">
      <img :src="trophyImage" alt="" aria-hidden="true" />
      <div>
        <p class="section-kicker">ACHIEVEMENT</p>
        <h1>{{ growth.title || "成长体系" }}</h1>
        <p>{{ growth.subtitle || "每天完成挑战，点亮自己的奖杯墙" }}</p>
      </div>
      <strong>Lv. {{ growth.level || 1 }}</strong>
    </div>

    <section class="growth-level-panel panel">
      <div class="growth-level-head">
        <span>当前积分</span>
        <strong>{{ growth.points || 0 }}</strong>
        <em>下一等级还差 {{ pointsToNextLevel }} 分</em>
      </div>
      <i class="growth-level-progress"><b :style="{ width: `${levelProgress}%` }"></b></i>
      <div v-if="rules.length" class="growth-score-rules">
        <span v-for="rule in rules" :key="rule.key">
          {{ rule.label }} +{{ rule.points }}
        </span>
      </div>
    </section>

    <section class="growth-detail-grid">
      <article
        v-for="item in metrics"
        :key="item.key"
        class="growth-detail-card panel"
        :class="[{ unlocked: item.unlocked }, `tier-${item.tier || 'gold'}`]"
      >
        <div class="growth-detail-medal">
          <img :src="item.iconUrl || trophyImage" alt="" aria-hidden="true" />
        </div>
        <div class="growth-detail-card-body">
          <span>{{ item.label }}</span>
          <strong>{{ badgeLabel(item) }}</strong>
          <p>{{ item.value }}/{{ item.target }}{{ item.unit || "" }}</p>
          <i><b :style="{ width: `${item.percent || 0}%` }"></b></i>
        </div>
      </article>
    </section>

    <section v-if="missions.length" class="growth-mission-panel panel">
      <div class="book-section-head">
        <span class="eyebrow">TODAY</span>
        <h3>每日任务</h3>
      </div>
      <div class="growth-mission-grid">
        <span v-for="mission in missions" :key="mission.key">
          <strong>{{ mission.label }}</strong>
          <em>{{ mission.value }}/{{ mission.target }}</em>
          <i><b :style="{ width: `${mission.percent || 0}%` }"></b></i>
        </span>
      </div>
    </section>
  </section>
</template>
