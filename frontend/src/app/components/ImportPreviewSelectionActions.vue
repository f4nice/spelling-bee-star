<script setup>
defineProps({
  setAllRows: {
    type: Function,
    required: true,
  },
  setAllColumns: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <button type="button" class="secondary-button" @click="setAllRows(true)">全选行</button>
  <button type="button" class="secondary-button" @click="setAllRows(false)">取消行</button>
  <button type="button" class="secondary-button" @click="setAllColumns(true)">全选列</button>
  <button type="button" class="secondary-button" @click="setAllColumns(false)">取消列</button>
</template>
