<script setup>
import ListDeleteNotice from "./ListDeleteNotice.vue";
import ListHeaderActions from "./ListHeaderActions.vue";
import ListTitleEditor from "./ListTitleEditor.vue";

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
  openImportModal: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <section class="panel upload-panel">
    <ListTitleEditor
      :word-list="data.word_list"
      :word-count="data.words.length"
      :rename-list="renameList"
      :open-import-modal="openImportModal"
    />
    <ListHeaderActions
      :delete-list-state="deleteListState"
      :rename-list="renameList"
      :delete-list="deleteList"
    />
    <ListDeleteNotice :notice="deleteListState.notice" />
  </section>
</template>
