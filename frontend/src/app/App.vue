<script setup>
import { computed } from "vue";
import AppShell from "./components/AppShell.vue";
import PageHeader from "./components/PageHeader.vue";
import PageOutlet from "./components/PageOutlet.vue";
import { useAppState } from "./composables/useAppState.js";

const { shellContext, route, data, routeTitle, loading, error, go, pageContext } = useAppState();

const hidePageHeader = computed(() => {
  const hiddenRoutes = ["admin", "catWorld", "challenge", "essays", "lists", "listDetail", "wrongWords", "spb", "newspaper", "newspaperArticle"];
  const routeName = route.value?.name || "";
  return hiddenRoutes.includes(routeName) || routeName.startsWith("booklearner");
});

function reloadPage() {
  window.location.reload();
}

function openLogin() {
  const next = `${window.location.pathname}${window.location.search}` || "/";
  window.location.assign(`/login?next=${encodeURIComponent(next)}`);
}
</script>

<template>
  <AppShell :route="route" :route-title="routeTitle" :shell="shellContext" :go="go">
    <PageHeader v-if="!hidePageHeader" :route-title="routeTitle" :route="route" :data="data" :go="go" />
    <div v-if="loading" class="empty-state">正在加载...</div>
    <div v-else-if="error" class="error-box app-error-box">
      <span>{{ error }}</span>
      <div class="app-error-actions">
        <button class="secondary-button compact-button" type="button" @click="reloadPage">刷新页面</button>
        <button class="secondary-button compact-button" type="button" @click="openLogin">重新登录</button>
      </div>
    </div>
    <PageOutlet v-else :ctx="pageContext" />
  </AppShell>
</template>
