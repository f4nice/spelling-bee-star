<script setup>
import { Moon, Sparkles } from "lucide-vue-next";

defineProps({ festival: { type: Object, required: true }, canShop: { type: Boolean, default: true } });
defineEmits(["details", "shop"]);
</script>

<template>
  <section v-if="festival.visible" class="cat-world-festival" aria-labelledby="cat-festival-title">
    <span class="cat-world-festival-moon" aria-hidden="true"><Moon :size="25" /><Sparkles :size="14" /></span>
    <div class="cat-world-festival-copy">
      <span class="cat-world-festival-dates">双节学习礼物 · {{ festival.dateLabel }}</span>
      <h2 id="cat-festival-title">ABBY，{{ festival.status === 'active' ? '节日学习能量翻倍啦！' : `${festival.name}快到啦，学习能量会翻倍！` }}</h2>
      <p>练拼写、写作文、说英语，新获学习能量再送一份，每天额外最多 500 点。还有 1500 能量的节日猫咪盲盒等你来看看。</p>
    </div>
    <div class="cat-world-festival-progress">
      <strong v-if="festival.status === 'active'">今日加赠 {{ festival.todayBonus }} / {{ festival.dailyCap }}</strong>
      <strong v-else>{{ festival.name }} · {{ festival.startDate?.slice(5).replace('-', '/') }} 开始</strong>
      <span v-if="festival.status === 'active'">{{ festival.remainingBonus ? `今天还可额外获得 ${festival.remainingBonus} 点` : '今日加赠已领满，安心休息一下吧' }}</span>
      <button type="button" class="secondary-button compact-button" @click="$emit('details')">看看活动规则</button>
      <button type="button" class="secondary-button compact-button" :disabled="!canShop" @click="$emit('shop')">{{ canShop ? '看看节庆盲盒' : '解锁陪伴时间后看盲盒' }}</button>
    </div>
  </section>
</template>
