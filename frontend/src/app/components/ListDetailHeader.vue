<script setup>
defineProps({
  data: {
    type: Object,
    required: true,
  },
  renameList: {
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
      <a class="ghost-button compact-button" href="/vue/upload">继续导入</a>
      <form :action="`/lists/${data.word_list.id}/delete`" method="post" class="delete-list-form">
        <input type="password" name="password" placeholder="删除密码" required>
        <button class="danger-button" type="submit">删除</button>
      </form>
    </div>
  </section>
</template>
