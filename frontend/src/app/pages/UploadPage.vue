<script setup>
import UploadExcelForm from "../components/UploadExcelForm.vue";
import { uploadExcelFormProps } from "../props/uploadExcelFormProps.js";

defineProps(uploadExcelFormProps);
</script>

<template>
  <section class="panel upload-panel">
    <div>
      <h1>导入 Excel</h1>
      <p>上传后会进入预览页，可以选择行、列和单词列。</p>
    </div>
  </section>

  <UploadExcelForm
    :upload-form="uploadForm"
    :upload-options="uploadOptions"
    :submit-upload="submitUpload"
  />
</template>
