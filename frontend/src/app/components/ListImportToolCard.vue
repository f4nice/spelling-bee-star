<script setup>
import UploadExcelForm from "./UploadExcelForm.vue";
import { uploadExcelFormProps } from "../props/uploadExcelFormProps.js";

defineProps(uploadExcelFormProps);
</script>

<template>
  <article class="tool-card">
    <div>
      <p class="section-kicker">Excel</p>
      <h2>导入单词</h2>
      <p>上传 Excel 后进入导入预览页。</p>
    </div>
    <UploadExcelForm
      :upload-options="uploadOptions"
      :upload-form="uploadForm"
      :submit-upload="submitUpload"
      variant="card"
    />
  </article>
</template>
