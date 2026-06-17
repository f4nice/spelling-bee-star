<script setup>
defineProps({
  deleteListState: {
    type: Object,
    required: true,
  },
  deleteList: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="delete-list-form" role="group" aria-label="删除单词表">
    <input v-model="deleteListState.password" type="password" placeholder="删除密码" required>
    <button class="danger-button" type="button" @click="deleteList">删除</button>
  </div>
</template>
