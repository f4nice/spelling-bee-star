<script setup>
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
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <section class="panel upload-panel">
    <ListTitleEditor :word-list="data.word_list" :word-count="data.words.length" />
    <ListHeaderActions
      :delete-list-state="deleteListState"
      :rename-list="renameList"
      :delete-list="deleteList"
      :go="go"
    />
    <p v-if="deleteListState.notice" class="notice">{{ deleteListState.notice }}</p>
  </section>
</template>
