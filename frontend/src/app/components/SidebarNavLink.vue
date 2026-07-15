<script setup>
defineProps({
  item: {
    type: Object,
    required: true,
  },
  navigate: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <a
    :class="{ active: item.active }"
    :href="item.path"
    @click.prevent="navigate(item.path)"
  >
    {{ item.label }} <span v-if="Number(item.count || 0) > 0" class="nav-count">{{ item.count }}</span>
  </a>
</template>
