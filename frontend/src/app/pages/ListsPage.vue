<script setup>
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
</script>

<template>
  <ListsToolsPanel
    :data="data"
    :upload-options="uploadOptions"
    :upload-form="uploadForm"
    :batch-image-state="batchImageState"
    :submit-upload="submitUpload"
    :submit-batch-images="submitBatchImages"
  />
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
