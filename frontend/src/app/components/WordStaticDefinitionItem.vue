<script setup>
defineProps({
  label: {
    type: String,
    required: true,
  },
  value: {
    type: String,
    default: "",
  },
});
</script>

<template>
  <dt>{{ label }}</dt>
  <dd>{{ value || "暂无" }}</dd>
</template>
