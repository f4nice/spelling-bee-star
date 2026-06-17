<script setup>
import { computed } from "vue";
import { buildSidebarNavItems } from "../sidebarNav.js";
import SidebarChallengeProgress from "./SidebarChallengeProgress.vue";

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

function navigate(path) {
  props.go(path);
}
</script>

<template>
  <aside class="sidebar">
    <nav class="side-nav" aria-label="主导航">
      <a
        v-for="item in navItems"
        :key="item.path"
        :class="{ active: item.active }"
        :href="item.path"
        @click.prevent="navigate(item.path)"
      >
        {{ item.label }} <span v-if="item.count !== undefined" class="nav-count">{{ item.count }}</span>
      </a>
      <SidebarChallengeProgress :challenges="shell.sidebarChallenges" :navigate="navigate" />
    </nav>
  </aside>
</template>
