<script setup>
import { defineAsyncComponent } from "vue";

const ChallengeDayPage = defineAsyncComponent(() => import("../pages/ChallengeDayPage.vue"));
const AdminPage = defineAsyncComponent(() => import("../pages/AdminPage.vue"));
const CatWorldPage = defineAsyncComponent(() => import("../pages/CatWorldPage.vue"));
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
  <CatWorldPage v-else-if="ctx.route.name === 'catWorld' && ctx.data" :data="ctx.data" />
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
