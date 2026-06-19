<script setup>
import ListDeleteControl from "./ListDeleteControl.vue";

defineProps({
  deleteListState: {
    type: Object,
    required: true,
  },
  renameList: {
    type: Function,
    required: true,
  },
  deleteList: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="list-actions">
    <ListDeleteControl :delete-list-state="deleteListState" :delete-list="deleteList" />
  </div>
</template>
