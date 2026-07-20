<script setup>
import { computed } from "vue";
import AppBrandLink from "./AppBrandLink.vue";
import AppDailyQuote from "./AppDailyQuote.vue";

const props = defineProps({
  shell: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});

const accountName = computed(() => props.shell.currentUser?.username || "我的账号");
const phoneLabel = computed(() => props.shell.currentUser?.phoneMasked || "");
</script>

<template>
  <header class="app-topbar">
    <AppBrandLink :app-name="shell.appName" :go="go" />
    <label class="menu-toggle" for="shellSidebarToggle" aria-label="缩放页面">☰</label>
    <AppDailyQuote :quote="shell.dailyQuote" />
    <details class="topbar-account-menu">
      <summary>
        <span>{{ accountName }}</span>
      </summary>
      <div class="topbar-account-panel">
        <strong>{{ accountName }}</strong>
        <span v-if="phoneLabel">{{ phoneLabel }}</span>
        <button
          v-if="shell.currentUser?.canAdmin"
          type="button"
          @click="go('/admin')"
        >
          后台管理
        </button>
        <form method="post" action="/logout">
          <button type="submit">退出登录</button>
        </form>
      </div>
    </details>
  </header>
</template>
