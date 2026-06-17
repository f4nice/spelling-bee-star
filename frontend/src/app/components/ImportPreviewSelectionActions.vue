<script setup>
import { importPreviewSelectionActionsProps } from "../props/importPreviewSelectionActionsProps.js";

defineProps(importPreviewSelectionActionsProps);
</script>

<template>
  <button type="button" class="secondary-button" @click="setAllRows(true)">全选行</button>
  <button type="button" class="secondary-button" @click="setAllRows(false)">取消行</button>
  <button type="button" class="secondary-button" @click="setAllColumns(true)">全选列</button>
  <button type="button" class="secondary-button" @click="setAllColumns(false)">取消列</button>
</template>
