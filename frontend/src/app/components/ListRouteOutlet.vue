<script setup>
import ListDetailRoute from "./ListDetailRoute.vue";
import ListOverviewRoute from "./ListOverviewRoute.vue";

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
