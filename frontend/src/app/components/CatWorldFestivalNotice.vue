<script setup>
import { Moon, Sparkles } from "lucide-vue-next";

defineProps({ festival: { type: Object, required: true }, canShop: { type: Boolean, default: true } });
defineEmits(["details", "shop"]);

function multiplierHeadline(festival) {
  const multiplier = Number(festival.todayMultiplier || 1);
  if (festival.status === "active") return `ABBY，今天学习能量 ${multiplier} 倍！`;
  if (multiplier > 1) return `ABBY，周末学习能量 ${multiplier} 倍，${festival.name}也快到啦！`;
  return `ABBY，${festival.name}快到啦，节庆日学习能量 3 倍！`;
}

function multiplierProgress(festival) {
  const multiplier = Number(festival.todayMultiplier || 1);
  if (festival.status === "active") return `今日加赠 ${festival.todayBonus || 0} / ${festival.dailyCap}`;
  if (multiplier > 1) return `今天周末 ${multiplier} 倍 · ${festival.name} ${festival.startDate?.slice(5).replace('-', '/')} 开始`;
  return `${festival.name} · ${festival.startDate?.slice(5).replace('-', '/')} 开始`;
}
</script>

<template>
  <section v-if="festival.visible" class="cat-world-festival" aria-labelledby="cat-festival-title">
    <span class="cat-world-festival-moon" aria-hidden="true"><Moon :size="25" /><Sparkles :size="14" /></span>
    <div class="cat-world-festival-copy">
      <span class="cat-world-festival-dates">节庆/周末学习礼物 · {{ festival.dateLabel }}</span>
      <h2 id="cat-festival-title">{{ multiplierHeadline(festival) }}</h2>
      <p>练拼写、写作文、说英语，普通周末新获能量 2 倍，节庆日 3 倍；每天额外最多 {{ festival.dailyCap }} 点。还有 1500 能量的节日猫咪盲盒和限定物品等你来看看。</p>
    </div>
    <div class="cat-world-festival-progress">
      <strong>{{ multiplierProgress(festival) }}</strong>
      <span v-if="festival.status === 'active'">{{ festival.remainingBonus ? `今天还可额外获得 ${festival.remainingBonus} 点` : '今日加赠已领满，安心休息一下吧' }}</span>
      <button type="button" class="secondary-button compact-button" @click="$emit('details')">看看活动规则</button>
      <button type="button" class="secondary-button compact-button" :disabled="!canShop" @click="$emit('shop')">{{ canShop ? '看看节庆盲盒' : '解锁陪伴时间后看盲盒' }}</button>
    </div>
  </section>
</template>
