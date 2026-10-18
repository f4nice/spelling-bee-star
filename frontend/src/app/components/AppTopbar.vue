<script setup>
import { computed } from "vue";
import AppBrandLink from "./AppBrandLink.vue";
import AppDailyQuote from "./AppDailyQuote.vue";
import { buildSidebarNavItems } from "../sidebarNav.js";

const props = defineProps({
  route: {
    type: Object,
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

const accountName = computed(() => props.shell.currentUser?.username || "我的账号");
const phoneLabel = computed(() => props.shell.currentUser?.phoneMasked || "");
const navItems = computed(() => buildSidebarNavItems({ route: props.route, shell: props.shell }));
const activeNavLabel = computed(() => navItems.value.find((item) => item.active)?.label || "导航");
</script>

<template>
  <header class="app-topbar">
    <AppBrandLink :app-name="shell.appName" :go="go" />
    <nav class="topbar-nav" aria-label="主导航">
      <a
        v-for="item in navItems"
        :key="item.path"
        :class="{ active: item.active }"
        :href="item.path"
        @click.prevent="go(item.path)"
      >
        <span>{{ item.label }}</span>
        <em v-if="Number(item.count || 0) > 0">{{ item.count }}</em>
      </a>
    </nav>
    <details class="mobile-nav-menu">
      <summary aria-label="打开主导航">
        <strong>{{ activeNavLabel }}</strong>
      </summary>
      <nav class="mobile-nav-grid" aria-label="移动端主导航">
        <a
          v-for="item in navItems"
          :key="item.path"
          :class="{ active: item.active }"
          :href="item.path"
          @click.prevent="go(item.path); $event.currentTarget.closest('details').open = false"
        >
          <span>{{ item.label }}</span>
          <em v-if="Number(item.count || 0) > 0">{{ item.count }}</em>
        </a>
      </nav>
    </details>
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
          class="topbar-admin-link"
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
