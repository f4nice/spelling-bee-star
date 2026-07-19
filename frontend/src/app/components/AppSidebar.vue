<script setup>
import { computed } from "vue";
import { buildSidebarNavItems } from "../sidebarNav.js";
import SidebarChallengeProgress from "./SidebarChallengeProgress.vue";
import SidebarGrowthPanel from "./SidebarGrowthPanel.vue";
import SidebarNavList from "./SidebarNavList.vue";

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

const navItems = computed(() => buildSidebarNavItems({ route: props.route, shell: props.shell }));
const phoneLabel = computed(() => props.shell.currentUser?.phoneMasked || "");

function navigate(path) {
  props.go(path);
}
</script>

<template>
  <aside class="sidebar">
    <nav class="side-nav" aria-label="主导航">
      <SidebarNavList :items="navItems" :navigate="navigate" />
      <SidebarGrowthPanel :growth="shell.learningGrowth" :navigate="navigate" />
      <SidebarChallengeProgress :challenges="shell.sidebarChallenges" :navigate="navigate" />
      <form class="sidebar-session" method="post" action="/logout">
        <span v-if="phoneLabel">已登录 {{ phoneLabel }}</span>
        <button
          v-if="phoneLabel"
          class="sidebar-admin-button"
          type="button"
          @click="navigate('/admin')"
        >
          后台管理
        </button>
        <button type="submit">退出登录</button>
      </form>
    </nav>
  </aside>
</template>
