<script setup>
import ChallengeDayPage from "../pages/ChallengeDayPage.vue";
import AdminPage from "../pages/AdminPage.vue";
import GrowthPage from "../pages/GrowthPage.vue";
import HomePage from "../pages/HomePage.vue";
import SpbPage from "../pages/SpbPage.vue";
import WrongWordsPage from "../pages/WrongWordsPage.vue";
import ListRouteOutlet from "./ListRouteOutlet.vue";
import NewspaperRouteOutlet from "./NewspaperRouteOutlet.vue";

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
  <GrowthPage v-else-if="ctx.route.name === 'growth' && ctx.data" :data="ctx.data" />
  <SpbPage v-else-if="ctx.route.name === 'spb' && ctx.data" :data="ctx.data" :go="ctx.go" />
  <ListRouteOutlet v-else-if="ctx.route.name === 'lists' || ctx.route.name === 'listDetail'" :ctx="ctx" />
  <NewspaperRouteOutlet v-else-if="ctx.route.name === 'newspaper' || ctx.route.name === 'newspaperArticle'" :ctx="ctx" />
  <WrongWordsPage v-else-if="ctx.route.name === 'wrongWords' && ctx.data" :data="ctx.data" :go="ctx.go" />
  <ChallengeDayPage v-else-if="ctx.route.name === 'challengeDay' && ctx.data" :data="ctx.data" :go="ctx.go" :fallback-letter="ctx.fallbackLetter" />
</template>
