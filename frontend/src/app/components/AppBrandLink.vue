<script setup>
const logoUrl = "/static/speakeasy-mouth-logo.svg";

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
  <a class="app-brand" href="/" @click.prevent="go('/')">
    <span class="brand-mark" aria-hidden="true">
      <img :src="logoUrl" alt="">
    </span>
    <span>{{ appName }}</span>
  </a>
</template>
