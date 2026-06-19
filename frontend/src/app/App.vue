<script setup>
import AppShell from "./components/AppShell.vue";
import PageHeader from "./components/PageHeader.vue";
import PageOutlet from "./components/PageOutlet.vue";
import { useAppState } from "./composables/useAppState.js";

const { shellContext, route, routeTitle, loading, error, go, pageContext } = useAppState();
</script>

<template>
  <AppShell :route="route" :route-title="routeTitle" :shell="shellContext" :go="go">
    <PageHeader v-if="!['challenge', 'lists'].includes(route.name)" :route-title="routeTitle" />
    <div v-if="loading" class="empty-state">正在加载...</div>
    <div v-else-if="error" class="error-box">{{ error }}</div>
    <PageOutlet v-else :ctx="pageContext" />
  </AppShell>
</template>
