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
const icpNumber = "沪ICP备2026026397号-2";
</script>

<template>
  <footer class="app-footer">
    <a class="app-footer-icp" href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">
      {{ icpNumber }}
    </a>
    <span class="app-footer-version">
      <span>{{ matrix.version }}</span>
      <span v-if="pageVersion">{{ pageVersion.text }}</span>
    </span>
  </footer>
</template>
