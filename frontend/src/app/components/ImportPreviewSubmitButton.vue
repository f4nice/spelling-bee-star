<script setup>
import { importPreviewSubmitButtonProps } from "../props/importPreviewSubmitButtonProps.js";

defineProps(importPreviewSubmitButtonProps);
</script>

<template>
  <button type="button" :disabled="isImporting" @click="submitImport">
    {{ isImporting ? "导入中..." : "确认导入" }}
  </button>
</template>
