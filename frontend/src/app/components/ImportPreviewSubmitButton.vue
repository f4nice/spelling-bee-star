<script setup>
import { importPreviewSubmitButtonProps } from "../props/importPreviewSubmitButtonProps.js";

defineProps(importPreviewSubmitButtonProps);
</script>

<template>
  <button type="button" @click="submitImport">确认导入</button>
</template>
