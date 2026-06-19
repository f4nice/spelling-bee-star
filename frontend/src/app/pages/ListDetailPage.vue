<script setup>
import { ref } from "vue";

import ListDetailHeader from "../components/ListDetailHeader.vue";
import ListDetailWordGrid from "../components/ListDetailWordGrid.vue";
import ListImageSyncPanel from "../components/ListImageSyncPanel.vue";
import ListImportToolCard from "../components/ListImportToolCard.vue";
import ListsCreateModal from "../components/ListsCreateModal.vue";

const props = defineProps([
  "data",
  "uploadOptions",
  "uploadForm",
  "deleteListState",
  "submitUpload",
  "renameList",
  "deleteList",
  "syncListImages",
  "wordDetailUrl",
  "imageForWord",
  "fallbackLetter",
  "go",
]);

const isImportModalOpen = ref(false);

function openImportModal() {
  const lists = props.uploadOptions.word_lists || [];
  if (!lists.some((item) => Number(item.id) === Number(props.data.word_list.id))) {
    props.uploadOptions.word_lists = [props.data.word_list, ...lists];
  }
  props.uploadForm.word_list_id = props.data.word_list.id;
  props.uploadForm.word_list_name = "";
  props.uploadForm.file = null;
  isImportModalOpen.value = true;
}
</script>

<template>
  <ListDetailHeader
    :data="data"
    :delete-list-state="deleteListState"
    :rename-list="renameList"
    :delete-list="deleteList"
    :open-import-modal="openImportModal"
  />
  <ListsCreateModal
    v-if="isImportModalOpen"
    kicker="Import"
    title="导入单词"
    description="上传 Excel 到当前单词表，确认预览后合并进来。"
    @close="isImportModalOpen = false"
  >
    <ListImportToolCard
      :upload-options="uploadOptions"
      :upload-form="uploadForm"
      :submit-upload="submitUpload"
    />
  </ListsCreateModal>
  <ListImageSyncPanel :sync-job="data.sync_job" :sync-list-images="syncListImages" />
  <ListDetailWordGrid
    :data="data"
    :word-detail-url="wordDetailUrl"
    :image-for-word="imageForWord"
    :fallback-letter="fallbackLetter"
  />
</template>
