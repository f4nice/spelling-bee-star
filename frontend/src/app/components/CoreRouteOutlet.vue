<script setup>
import ChallengeDayPage from "../pages/ChallengeDayPage.vue";
import HomePage from "../pages/HomePage.vue";
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
  <ListRouteOutlet v-else-if="ctx.route.name === 'lists' || ctx.route.name === 'listDetail'" :ctx="ctx" />
  <NewspaperRouteOutlet v-else-if="ctx.route.name === 'newspaper' || ctx.route.name === 'newspaperArticle'" :ctx="ctx" />
  <WrongWordsPage v-else-if="ctx.route.name === 'wrongWords' && ctx.data" :data="ctx.data" :go="ctx.go" />
  <ChallengeDayPage v-else-if="ctx.route.name === 'challengeDay' && ctx.data" :data="ctx.data" :go="ctx.go" :fallback-letter="ctx.fallbackLetter" />
</template>
