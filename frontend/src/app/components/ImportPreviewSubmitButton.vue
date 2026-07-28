<script setup>
import { computed } from "vue";
import { importPreviewJobPercent } from "../importPreviewJob.js";
import { importPreviewSubmitButtonProps } from "../props/importPreviewSubmitButtonProps.js";

const props = defineProps(importPreviewSubmitButtonProps);
const percent = computed(() => importPreviewJobPercent(props.importJob));
</script>

<template>
  <button type="button" :disabled="isImporting" @click="submitImport">
    {{ isImporting ? `导入中 ${percent}%` : "确认导入" }}
  </button>
</template>
