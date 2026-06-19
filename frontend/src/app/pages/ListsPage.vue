<script setup>
import { ref } from "vue";
import ListsCreateModal from "../components/ListsCreateModal.vue";
import ListsToolsPanel from "../components/ListsToolsPanel.vue";
import WordListCard from "../components/WordListCard.vue";

defineProps([
  "data",
  "uploadOptions",
  "uploadForm",
  "batchImageState",
  "submitUpload",
  "submitBatchImages",
  "fallbackLetter",
  "go",
]);

const isCreateModalOpen = ref(false);
</script>

<template>
  <section class="panel app-page-heading lists-page-heading">
    <div>
      <p class="section-kicker">SpeakEasy</p>
      <h1>我的单词表</h1>
    </div>
    <button class="primary-action-button" type="button" @click="isCreateModalOpen = true">
      新建单词表
    </button>
  </section>
  <ListsCreateModal v-if="isCreateModalOpen" @close="isCreateModalOpen = false">
    <ListsToolsPanel
      :data="data"
      :upload-options="uploadOptions"
      :upload-form="uploadForm"
      :batch-image-state="batchImageState"
      :submit-upload="submitUpload"
      :submit-batch-images="submitBatchImages"
    />
  </ListsCreateModal>
  <section class="word-grid">
    <WordListCard
      v-for="card in data.cards"
      :key="card.list.id"
      :card="card"
      :fallback-letter="fallbackLetter"
      :go="go"
      show-challenge
    />
  </section>
</template>
