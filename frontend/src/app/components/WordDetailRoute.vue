<script setup>
import { computed, defineAsyncComponent } from "vue";
import { buildWordDetailPageProps } from "../wordDetailPageProps.js";

const WordDetailPage = defineAsyncComponent(() => import("../pages/WordDetailPage.vue"));

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
