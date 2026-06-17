<script setup>
import { computed } from "vue";

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

const navItems = computed(() => [
  { label: "首页", path: "/", active: props.route.name === "home" },
  { label: "我的单词表", path: "/lists", active: props.route.name === "lists" || props.route.name === "listDetail" },
  { label: "英文小报", path: "/newspaper", active: props.route.name.startsWith("newspaper") },
  { label: "好词好句", path: "/booklearner", active: props.route.name.startsWith("booklearner") },
  { label: "我的生词本", path: "/wrong-words", active: props.route.name === "wrongWords", count: props.shell.wrongWordCount },
]);

const quoteText = computed(() => props.shell.dailyQuote?.content || "Every word is a new window.");
const logoUrl = "/static/speakeasy-mouth-logo.svg";

function navigate(path) {
  props.go(path);
}
</script>

<template>
  <input class="shell-sidebar-toggle" id="shellSidebarToggle" type="checkbox" aria-hidden="true">
  <header class="app-topbar">
    <a class="app-brand" href="/" @click.prevent="navigate('/')">
      <span class="brand-mark" aria-hidden="true">
        <img :src="logoUrl" alt="">
      </span>
      <span>{{ shell.appName }}</span>
    </a>
    <label class="menu-toggle" for="shellSidebarToggle" aria-label="缩放页面">☰</label>
    <div class="daily-quote">
      {{ quoteText }}<span v-if="shell.dailyQuote?.author"> - {{ shell.dailyQuote.author }}</span>
    </div>
  </header>

  <div class="app-layout">
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

    <main class="shell" :aria-label="routeTitle">
      <slot />
    </main>
  </div>
</template>
