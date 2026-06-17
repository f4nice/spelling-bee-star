<script setup>
import ListHeaderActions from "./ListHeaderActions.vue";

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
    <ListHeaderActions
      :delete-list-state="deleteListState"
      :rename-list="renameList"
      :delete-list="deleteList"
      :go="go"
    />
    <p v-if="deleteListState.notice" class="notice">{{ deleteListState.notice }}</p>
  </section>
</template>
