<script setup>
import { computed } from "vue";

import UploadExcelCardFields from "./UploadExcelCardFields.vue";
import UploadExcelPageFields from "./UploadExcelPageFields.vue";
import VersionStamp from "./VersionStamp.vue";
import { uploadExcelFormProps } from "../props/uploadExcelFormProps.js";

const props = defineProps(uploadExcelFormProps);

const isCard = computed(() => props.variant === "card");

const formClasses = computed(() => [
  isCard.value ? "home-upload-form" : "panel upload-form wide-form",
]);

const fieldsComponent = computed(() => (
  isCard.value ? UploadExcelCardFields : UploadExcelPageFields
));
</script>

<template>
  <div :class="formClasses" role="group" aria-label="导入单词">
    <component
      :is="fieldsComponent"
      :upload-options="uploadOptions"
      :upload-form="uploadForm"
      :submit-upload="submitUpload"
    />
    <VersionStamp label="上传导入" />
  </div>
</template>
