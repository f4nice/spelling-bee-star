<script setup>
import ListsToolsPanel from "../components/ListsToolsPanel.vue";
import WordListCard from "../components/WordListCard.vue";

defineProps([
  "data",
  "uploadOptions",
  "uploadForm",
  "submitUpload",
  "fallbackLetter",
  "go"
]);
</script>

<template>
  <ListsToolsPanel
    :data="data"
    :upload-options="uploadOptions"
    :upload-form="uploadForm"
    :submit-upload="submitUpload"
  />
  <section class="word-grid">
    <WordListCard
      v-for="card in data.cards"
      :key="card.list.id"
      :card="card"
      :go="go"
      :fallback-letter="fallbackLetter"
      show-challenge
    />
  </section>
</template>
