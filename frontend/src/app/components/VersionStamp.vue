<script setup>
import { computed } from "vue";
import { versionForLabel } from "../pageVersion.js";
import { readVersionMatrix } from "../versionInfo.js";

const props = defineProps({
  label: {
    type: String,
    default: "版本",
  },
});

const version = computed(() => readVersionMatrix());
const moduleVersion = computed(() => versionForLabel(version.value, props.label));
</script>

<template>
  <div class="version-stamp" aria-label="版本信息">
    <span>{{ label }}</span>
    <strong>{{ moduleVersion }}</strong>
  </div>
</template>
