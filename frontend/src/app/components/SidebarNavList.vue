<script setup>
import SidebarNavLink from "./SidebarNavLink.vue";

defineProps({
  items: {
    type: Array,
    required: true,
  },
  navigate: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <SidebarNavLink
    v-for="item in items"
    :key="item.path"
    :item="item"
    :navigate="navigate"
  />
</template>
