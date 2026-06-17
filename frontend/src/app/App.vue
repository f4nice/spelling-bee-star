<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import AppShell from "./components/AppShell.vue";
import PageHeader from "./components/PageHeader.vue";
import PageOutlet from "./components/PageOutlet.vue";
import { useAppRouteController } from "./appRouteController.js";
import { useBooklearner } from "./composables/useBooklearner.js";
import { useImportPreview } from "./composables/useImportPreview.js";
import { useListTools } from "./composables/useListTools.js";
import { useWordDetail } from "./composables/useWordDetail.js";
import { usePageContext } from "./pageContext.js";
import { routeTitle as titleForRoute } from "./router.js";
import { useShellContext } from "./shellContext.js";

const data = ref(null);
const { shellContext, refreshShellContext } = useShellContext();
const { route, loading, error, setError, go, loadRoute, onPopState } = useAppRouteController({
  data,
  refreshShellContext,
  getRouteLoaders: () => ({
    resetWordTools,
    setWordEdit,
    setUploadOptionsFromCards,
    loadUploadOptions,
    resetImportForm,
    loadBooklearner,
  }),
});

const routeTitle = computed(() => titleForRoute(route.value, data.value));

const importPreview = useImportPreview({ data, route, go, loadRoute, setError });
const { resetImportForm } = importPreview;

const wordDetail = useWordDetail({ data, loadRoute });
const { resetWordTools, setWordEdit, handleWordKeydown } = wordDetail;

const booklearner = useBooklearner({ route, go });
const { loadBooklearner } = booklearner;

const listTools = useListTools({ data, go, loadRoute });
const { setUploadOptionsFromCards, loadUploadOptions } = listTools;

const pageContext = usePageContext({ route, data, go, importPreview, wordDetail, booklearner, listTools });

function onKeydown(event) {
  handleWordKeydown(event, route.value);
}

onMounted(() => {
  window.addEventListener("popstate", onPopState);
  window.addEventListener("keydown", onKeydown);
  loadRoute();
});

onUnmounted(() => {
  window.removeEventListener("popstate", onPopState);
  window.removeEventListener("keydown", onKeydown);
});
</script>

<template>
  <AppShell :route="route" :route-title="routeTitle" :shell="shellContext" :go="go">
    <PageHeader :route-title="routeTitle" :go="go" />
    <div v-if="loading" class="empty-state">正在加载...</div>
    <div v-else-if="error" class="error-box">{{ error }}</div>
    <PageOutlet v-else :ctx="pageContext" />
  </AppShell>
</template>
