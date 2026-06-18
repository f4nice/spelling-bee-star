<script setup>
import HomeFeaturedListGrid from "./HomeFeaturedListGrid.vue";
import HomeFeaturedListsHeading from "./HomeFeaturedListsHeading.vue";

defineProps({
  cards: {
    type: Array,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
  fallbackLetter: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <HomeFeaturedListsHeading :go="go" />
  <HomeFeaturedListGrid :cards="cards" :go="go" :fallback-letter="fallbackLetter" />
</template>
