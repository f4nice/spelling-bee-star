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
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="list-actions">
    <button class="secondary-button" type="button" @click="renameList">保存名称</button>
    <button class="ghost-button compact-button" type="button" @click="go('/upload')">继续导入</button>
    <ListDeleteControl :delete-list-state="deleteListState" :delete-list="deleteList" />
  </div>
</template>
