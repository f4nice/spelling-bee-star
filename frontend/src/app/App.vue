<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import VuePageHeader from "./components/VuePageHeader.vue";
import VuePageOutlet from "./components/VuePageOutlet.vue";
import { useBooklearner } from "./composables/useBooklearner.js";
import { useImportPreview } from "./composables/useImportPreview.js";
import { useListTools } from "./composables/useListTools.js";
import { useWordDetail } from "./composables/useWordDetail.js";
import { usePageContext } from "./pageContext.js";
import { loadVueRouteData } from "./routeDataLoader.js";
import { oldPathFor, parseRoute, routeTitle as titleForRoute } from "./router.js";

const route = ref(parseRoute());
const data = ref(null);
const loading = ref(false);
const error = ref("");

const routeTitle = computed(() => titleForRoute(route.value, data.value));
const legacyHref = computed(() => oldPathFor(window.location.pathname));

function setError(message) {
  error.value = message;
}

function go(path) {
  const prefix = window.location.pathname.startsWith("/vue") ? "/vue" : "";
  history.pushState(null, "", `${prefix}${path}`);
  route.value = parseRoute();
  loadRoute();
}

const importPreview = useImportPreview({ data, route, go, loadRoute, setError });
const { resetImportForm } = importPreview;

const wordDetail = useWordDetail({ data, loadRoute });
const { resetWordTools, setWordEdit, handleWordKeydown } = wordDetail;

const booklearner = useBooklearner({ route, go });
const { loadBooklearner } = booklearner;

const listTools = useListTools({ data, go, loadRoute });
const { setUploadOptionsFromCards, loadUploadOptions } = listTools;

const pageContext = usePageContext({ route, data, go, importPreview, wordDetail, booklearner, listTools });

function onPopState() {
  route.value = parseRoute();
  loadRoute();
}

async function loadRoute() {
  if (route.value.name === "challenge") {
    data.value = null;
    error.value = "";
    return;
  }

  loading.value = true;
  error.value = "";
  try {
    await loadVueRouteData({
      route: route.value,
      data,
      resetWordTools,
      setWordEdit,
      setUploadOptionsFromCards,
      loadUploadOptions,
      resetImportForm,
      loadBooklearner,
    });
  } catch (err) {
    error.value = err.message || "页面数据加载失败";
  } finally {
    loading.value = false;
  }
}

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
  <VuePageHeader :route-title="routeTitle" :legacy-href="legacyHref" :go="go" />
  <div v-if="loading" class="empty-state">正在加载...</div>
  <div v-else-if="error" class="error-box">{{ error }}</div>
  <VuePageOutlet v-else :ctx="pageContext" />
</template>
