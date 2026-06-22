<script setup>
import { computed } from "vue";
import { readVersionMatrix } from "../versionInfo.js";

const props = defineProps({
  label: {
    type: String,
    default: "版本",
  },
});

const version = computed(() => readVersionMatrix());
</script>

<template>
  <div class="version-stamp" aria-label="版本信息">
    <span>{{ label }}</span>
    <strong>{{ version.version }}</strong>
    <small v-if="version.machineCode">{{ version.machineCode }}</small>
  </div>
</template>
