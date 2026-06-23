<script setup>
import { computed } from "vue";
import { normalizeVersionMatrix } from "../versionInfo.js";

const props = defineProps({
  version: {
    type: Object,
    default: null,
  },
  pageVersion: {
    type: Object,
    default: null,
  },
});

const matrix = computed(() => normalizeVersionMatrix(props.version));
</script>

<template>
  <footer class="app-footer">
    <span>{{ matrix.footerText }}</span>
    <span>{{ matrix.version }}</span>
    <span v-if="pageVersion">{{ pageVersion.text }}</span>
  </footer>
</template>
