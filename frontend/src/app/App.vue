<script setup>
import { computed } from "vue";
import AppShell from "./components/AppShell.vue";
import PageHeader from "./components/PageHeader.vue";
import PageOutlet from "./components/PageOutlet.vue";
import { useAppState } from "./composables/useAppState.js";

const { shellContext, route, data, routeTitle, loading, error, go, pageContext } = useAppState();

const hidePageHeader = computed(() => {
  const hiddenRoutes = ["challenge", "lists", "listDetail", "wrongWords", "newspaper", "newspaperArticle"];
  const routeName = route.value?.name || "";
  return hiddenRoutes.includes(routeName) || routeName.startsWith("booklearner");
});
</script>

<template>
  <AppShell :route="route" :route-title="routeTitle" :shell="shellContext" :go="go">
    <PageHeader v-if="!hidePageHeader" :route-title="routeTitle" :route="route" :data="data" :go="go" />
    <div v-if="loading" class="empty-state">正在加载...</div>
    <div v-else-if="error" class="error-box">{{ error }}</div>
    <PageOutlet v-else :ctx="pageContext" />
  </AppShell>
</template>
