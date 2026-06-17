<script setup>
import { computed } from "vue";
import WordDetailPage from '../pages/WordDetailPage.vue';
import { buildWordDetailPageProps } from "../wordDetailPageProps.js";

const props = defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});

const pageProps = computed(() => buildWordDetailPageProps(props.ctx));
</script>

<template>
  <WordDetailPage v-bind="pageProps" />
</template>
