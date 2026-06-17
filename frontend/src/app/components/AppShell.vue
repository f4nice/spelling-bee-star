<script setup>
import AppSidebar from "./AppSidebar.vue";
import AppTopbar from "./AppTopbar.vue";

defineProps({
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
</script>

<template>
  <input class="shell-sidebar-toggle" id="shellSidebarToggle" type="checkbox" aria-hidden="true">
  <AppTopbar :shell="shell" :go="go" />

  <div class="app-layout">
    <AppSidebar :route="route" :shell="shell" :go="go" />

    <main class="shell" :aria-label="routeTitle">
      <slot />
    </main>
  </div>
</template>
