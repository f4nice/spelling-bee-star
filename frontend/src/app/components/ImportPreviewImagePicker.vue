<script setup>
import { setImportPreviewImages } from "../forms/importPreviewImageHandlers.js";
import { importPreviewImagePickerProps } from "../props/importPreviewImagePickerProps.js";

defineProps(importPreviewImagePickerProps);
</script>

<template>
  <label>
    批量图片
    <input
      type="file"
      accept="image/*"
      multiple
      webkitdirectory
      directory
      @change="setImportPreviewImages(importForm, $event)"
    >
  </label>
</template>
