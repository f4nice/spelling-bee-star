<script setup>
import { defineAsyncComponent } from "vue";

const ChallengeDayPage = defineAsyncComponent(() => import("../pages/ChallengeDayPage.vue"));
const AdminPage = defineAsyncComponent(() => import("../pages/AdminPage.vue"));
const CatWorldPage = defineAsyncComponent(() => import("../pages/CatWorldPage.vue"));
const FunMathPage = defineAsyncComponent(() => import("../pages/FunMathPage.vue"));
const DebatePage = defineAsyncComponent(() => import("../pages/DebatePage.vue"));
const DiaryPage = defineAsyncComponent(() => import("../pages/DiaryPage.vue"));
const EssaysPage = defineAsyncComponent(() => import("../pages/EssaysPage.vue"));
const GrowthPage = defineAsyncComponent(() => import("../pages/GrowthPage.vue"));
const HomePage = defineAsyncComponent(() => import("../pages/HomePage.vue"));
const SpbPage = defineAsyncComponent(() => import("../pages/SpbPage.vue"));
const WrongWordsPage = defineAsyncComponent(() => import("../pages/WrongWordsPage.vue"));
const ListRouteOutlet = defineAsyncComponent(() => import("./ListRouteOutlet.vue"));
const NewspaperRouteOutlet = defineAsyncComponent(() => import("./NewspaperRouteOutlet.vue"));

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <HomePage v-if="ctx.route.name === 'home' && ctx.data" :data="ctx.data" :go="ctx.go" :fallback-letter="ctx.fallbackLetter" />
  <AdminPage v-else-if="ctx.route.name === 'admin' && ctx.data" :data="ctx.data" />
  <section v-else-if="ctx.route.name === 'catWorld' && ctx.data?.read_only" class="panel">
    <h1>{{ ctx.data.owner_name }} 的猫咪世界</h1>
    <p>只读查看，不会触发喂养、消耗或积分变化。</p>
    <p v-if="!ctx.data.has_data">这个账号还没有猫咪世界数据。</p>
    <template v-else>
      <h2>已拥有的猫咪</h2>
      <ul><li v-for="cat in ctx.data.cats" :key="cat.id">{{ cat.name }}</li></ul>
      <h2>背包物品</h2>
      <ul><li v-for="item in ctx.data.inventory" :key="item.id">{{ item.id }} × {{ item.count }}</li></ul>
      <p>累计消耗能量：{{ ctx.data.energy_spent }}</p>
    </template>
  </section>
  <CatWorldPage v-else-if="ctx.route.name === 'catWorld' && ctx.data" :data="ctx.data" />
  <section v-else-if="ctx.route.name === 'funMath' && ctx.data?.read_only" class="panel">
    <h1>{{ ctx.data.owner_name }} 的趣味数学记录</h1><p>只读查看，不生成新题或发放奖励。</p>
    <p v-if="!ctx.data.history.length">还没有答题记录。</p>
    <ul><li v-for="day in ctx.data.history" :key="day.day">{{ day.day }} · 已完成 {{ day.completed }} 题，答对 {{ day.correct }} 题</li></ul>
  </section>
  <FunMathPage v-else-if="ctx.route.name === 'funMath' && ctx.data" :data="ctx.data" :go="ctx.go" />
  <DebatePage v-else-if="ctx.route.name === 'debate' && ctx.data" :data="ctx.data" />
  <DiaryPage v-else-if="ctx.route.name === 'diary' && ctx.data" :data="ctx.data" />
  <EssaysPage v-else-if="ctx.route.name === 'essays' && ctx.data" :data="ctx.data" />
  <GrowthPage v-else-if="ctx.route.name === 'growth' && ctx.data" :data="ctx.data" />
  <SpbPage v-else-if="ctx.route.name === 'spb' && ctx.data" :data="ctx.data" :go="ctx.go" />
  <ListRouteOutlet v-else-if="ctx.route.name === 'lists' || ctx.route.name === 'listDetail'" :ctx="ctx" />
  <NewspaperRouteOutlet v-else-if="ctx.route.name === 'newspaper' || ctx.route.name === 'newspaperArticle'" :ctx="ctx" />
  <WrongWordsPage v-else-if="ctx.route.name === 'wrongWords' && ctx.data" :data="ctx.data" :go="ctx.go" />
  <ChallengeDayPage v-else-if="ctx.route.name === 'challengeDay' && ctx.data" :data="ctx.data" :go="ctx.go" :fallback-letter="ctx.fallbackLetter" />
</template>
