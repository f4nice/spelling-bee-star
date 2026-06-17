<script setup>
import BooklearnerRouteOutlet from "./BooklearnerRouteOutlet.vue";
import ChallengeRouteOutlet from "./ChallengeRouteOutlet.vue";
import CoreRouteOutlet from "./CoreRouteOutlet.vue";
import ImportRouteOutlet from "./ImportRouteOutlet.vue";
import WordDetailRoute from "./WordDetailRoute.vue";

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <ChallengeRouteOutlet v-if="ctx.route.name === 'challenge'" :route="ctx.route" />
  <WordDetailRoute v-else-if="ctx.route.name === 'wordDetail' && ctx.data" :ctx="ctx" />
  <ImportRouteOutlet v-else-if="(ctx.route.name === 'upload' || ctx.route.name === 'preview') && ctx.data" :ctx="ctx" />
  <BooklearnerRouteOutlet v-else-if="ctx.route.name.startsWith('booklearner') && ctx.data" :ctx="ctx" />
  <CoreRouteOutlet v-else :ctx="ctx" />
</template>
