<script setup>
import AppBrandLink from "./AppBrandLink.vue";
import AppDailyQuote from "./AppDailyQuote.vue";

defineProps({
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
  <header class="app-topbar">
    <AppBrandLink :app-name="shell.appName" :go="go" />
    <label class="menu-toggle" for="shellSidebarToggle" aria-label="缩放页面">☰</label>
    <AppDailyQuote :quote="shell.dailyQuote" />
  </header>
</template>
