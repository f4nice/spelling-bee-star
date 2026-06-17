<script setup>
defineProps({
  data: {
    type: Object,
    required: true,
  },
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
  <section class="panel upload-panel">
    <div>
      <input v-model="data.word_list.name" class="list-title-input">
      <p>{{ data.words.length }} 个单词</p>
    </div>
    <div class="list-actions">
      <button class="secondary-button" type="button" @click="renameList">保存名称</button>
      <button class="ghost-button compact-button" type="button" @click="go('/upload')">继续导入</button>
      <div class="delete-list-form" role="group" aria-label="删除单词表">
        <input v-model="deleteListState.password" type="password" placeholder="删除密码" required>
        <button class="danger-button" type="button" @click="deleteList">删除</button>
      </div>
    </div>
    <p v-if="deleteListState.notice" class="notice">{{ deleteListState.notice }}</p>
  </section>
</template>
