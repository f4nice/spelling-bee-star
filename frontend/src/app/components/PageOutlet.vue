<script setup>
import BooklearnerRouteOutlet from "./BooklearnerRouteOutlet.vue";
import ChallengeRouteOutlet from "./ChallengeRouteOutlet.vue";
import CoreRouteOutlet from "./CoreRouteOutlet.vue";
import ImportRouteOutlet from "./ImportRouteOutlet.vue";
import WordDetailRoute from "./WordDetailRoute.vue";
import {
  isBooklearnerRoute,
  isChallengeRoute,
  isImportRoute,
  isWordDetailRoute,
} from "../pageOutletRoutes.js";

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <ChallengeRouteOutlet v-if="isChallengeRoute(ctx.route)" :route="ctx.route" />
  <WordDetailRoute v-else-if="isWordDetailRoute(ctx.route) && ctx.data" :ctx="ctx" />
  <ImportRouteOutlet v-else-if="isImportRoute(ctx.route) && ctx.data" :ctx="ctx" />
  <BooklearnerRouteOutlet v-else-if="isBooklearnerRoute(ctx.route) && ctx.data" :ctx="ctx" />
  <CoreRouteOutlet v-else :ctx="ctx" />
</template>
