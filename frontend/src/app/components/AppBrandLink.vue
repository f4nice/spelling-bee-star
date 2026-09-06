<script setup>
const logoUrl = "/static/newabby-logo.svg";

defineProps({
  appName: {
    type: String,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <a class="app-brand app-brand-newabby" href="/" aria-label="NEWABBY 首页" @click.prevent="go('/')">
    <img class="newabby-logo" :src="logoUrl" alt="NEWABBY" width="190" height="45">
  </a>
</template>

<style scoped>
.app-brand-newabby { gap: 0; line-height: 0; border-radius: 8px; }
.newabby-logo { display: block; width: 190px; height: auto; transition: transform 180ms ease; }
.app-brand-newabby:hover .newabby-logo { transform: translateY(-1px) rotate(-1deg); }
.app-brand-newabby:focus-visible { outline: 2px solid #ffda74; outline-offset: 5px; }
@media (max-width: 600px) { .newabby-logo { width: 158px; } }
@media (prefers-reduced-motion: reduce) { .newabby-logo { transition: none; } .app-brand-newabby:hover .newabby-logo { transform: none; } }
</style>
