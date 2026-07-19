<script setup>
import { defineAsyncComponent } from "vue";

const ListDetailRoute = defineAsyncComponent(() => import("./ListDetailRoute.vue"));
const ListOverviewRoute = defineAsyncComponent(() => import("./ListOverviewRoute.vue"));

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <ListOverviewRoute v-if="ctx.route.name === 'lists'" :ctx="ctx" />
  <ListDetailRoute v-else-if="ctx.route.name === 'listDetail'" :ctx="ctx" />
</template>
