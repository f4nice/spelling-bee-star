<script setup>
import { computed } from "vue";

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

const quoteText = computed(() => props.shell.dailyQuote?.content || "Every word is a new window.");
const logoUrl = "/static/speakeasy-mouth-logo.svg";

function navigate(path) {
  props.go(path);
}
</script>

<template>
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
</template>
