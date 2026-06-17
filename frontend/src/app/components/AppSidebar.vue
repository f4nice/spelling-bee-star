<script setup>
import { computed } from "vue";

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

const navItems = computed(() => [
  { label: "首页", path: "/", active: props.route.name === "home" },
  { label: "我的单词表", path: "/lists", active: props.route.name === "lists" || props.route.name === "listDetail" },
  { label: "英文小报", path: "/newspaper", active: props.route.name.startsWith("newspaper") },
  { label: "好词好句", path: "/booklearner", active: props.route.name.startsWith("booklearner") },
  { label: "我的生词本", path: "/wrong-words", active: props.route.name === "wrongWords", count: props.shell.wrongWordCount },
]);

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

      <div class="challenge-sidebar">
        <div class="challenge-sidebar-title">挑战进度</div>
        <a
          v-for="item in shell.sidebarChallenges"
          :key="item.id"
          class="challenge-progress-link"
          :href="`/challenge/${item.id}`"
          @click.prevent="navigate(`/challenge/${item.id}`)"
        >
          <strong>{{ item.name }}</strong>
          <span>{{ item.completed }} / {{ item.total }}</span>
          <div class="sidebar-progress"><i :style="{ width: `${item.percent}%` }"></i></div>
        </a>
        <p v-if="!shell.sidebarChallenges.length">还没有可挑战的单词表。</p>
      </div>
    </nav>
  </aside>
</template>
