<script setup>
import ListDeleteNotice from "./ListDeleteNotice.vue";
import ListHeaderActions from "./ListHeaderActions.vue";
import ListTitleEditor from "./ListTitleEditor.vue";
import { ref } from "vue";
import { fetchJson } from "../utils.js";

const copyNotice=ref("");
const copying=ref(false);
async function copyPublicList(id) {
  copying.value=true;
  try {
    const result=await fetchJson(`/api/vue/lists/${id}/personal-copy`,{ method:"POST" });
    window.location.assign(result.url);
  } catch (error) { copyNotice.value=error.message; }
  finally { copying.value=false; }
}

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
  moveListToGroup: {
    type: Function,
    required: true,
  },
  openCreateWordModal: {
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
    <div v-if="data.can_manage === false">
      <h1>{{ data.word_list.name }}</h1>
      <p>{{ data.words.length }} 个单词 · {{ data.is_public ? '官方公共词库，只读' : '正在只读查看' }}</p>
      <button v-if="data.can_copy" type="button" :disabled="copying" @click="copyPublicList(data.word_list.id)">复制到我的词表</button>
      <p v-if="copyNotice" role="alert">{{ copyNotice }}</p>
    </div>
    <ListTitleEditor v-else
      :word-list="data.word_list"
      :word-count="data.words.length"
      :groups="data.groups || []"
      :move-list-to-group="moveListToGroup"
      :rename-list="renameList"
      :open-create-word-modal="openCreateWordModal"
      :open-import-modal="openImportModal"
    />
    <ListHeaderActions
      v-if="data.can_manage !== false"
      :delete-list-state="deleteListState"
      :rename-list="renameList"
      :delete-list="deleteList"
    />
    <ListDeleteNotice :notice="deleteListState.notice" />
  </section>
</template>
