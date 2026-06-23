<script setup>
import { computed } from "vue";
import AppFooter from "./AppFooter.vue";
import AppSidebar from "./AppSidebar.vue";
import AppTopbar from "./AppTopbar.vue";
import { pageVersionForRoute } from "../pageVersion.js";

const props = defineProps({
  route: {
    type: Object,
    required: true,
  },
  routeTitle: {
    type: String,
    required: true,
  },
  shell: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});

const pageVersion = computed(() => pageVersionForRoute(props.route, props.shell.versionMatrix));
</script>

<template>
  <input class="shell-sidebar-toggle" id="shellSidebarToggle" type="checkbox" aria-hidden="true">
  <AppTopbar :shell="shell" :go="go" />

  <div class="app-layout">
    <AppSidebar :route="route" :shell="shell" :go="go" />

    <main
      class="shell"
      :aria-label="routeTitle"
      :quant-radar-page-key="pageVersion.key"
      :quant-radar-page-label="pageVersion.label"
      :quant-radar-page-version="pageVersion.version"
      :quant-radar-page-version-text="pageVersion.text"
      :data-quant-radar-page-key="pageVersion.key"
      :data-quant-radar-page-label="pageVersion.label"
      :data-quant-radar-page-version="pageVersion.version"
      :data-quant-radar-page-version-text="pageVersion.text"
    >
      <slot />
      <AppFooter :version="shell.versionMatrix" :page-version="pageVersion" />
    </main>
  </div>
</template>
