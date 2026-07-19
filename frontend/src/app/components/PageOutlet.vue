<script setup>
import { defineAsyncComponent } from "vue";
import {
  isBooklearnerRoute,
  isChallengeRoute,
  isImportRoute,
  isWordDetailRoute,
} from "../pageOutletRoutes.js";

const BooklearnerRouteOutlet = defineAsyncComponent(() => import("./BooklearnerRouteOutlet.vue"));
const ChallengeRouteOutlet = defineAsyncComponent(() => import("./ChallengeRouteOutlet.vue"));
const CoreRouteOutlet = defineAsyncComponent(() => import("./CoreRouteOutlet.vue"));
const ImportRouteOutlet = defineAsyncComponent(() => import("./ImportRouteOutlet.vue"));
const WordDetailRoute = defineAsyncComponent(() => import("./WordDetailRoute.vue"));

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
