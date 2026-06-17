<script setup>
import ListDetailHeader from "../components/ListDetailHeader.vue";
import ListDetailWordGrid from "../components/ListDetailWordGrid.vue";
import ListImageSyncPanel from "../components/ListImageSyncPanel.vue";

defineProps([
  "data",
  "deleteListState",
  "renameList",
  "deleteList",
  "syncListImages",
  "wordDetailUrl",
  "imageForWord",
  "fallbackLetter",
  "go",
]);
</script>

<template>
  <ListDetailHeader
    :data="data"
    :delete-list-state="deleteListState"
    :rename-list="renameList"
    :delete-list="deleteList"
    :go="go"
  />
  <ListImageSyncPanel :sync-job="data.sync_job" :sync-list-images="syncListImages" />
  <ListDetailWordGrid
    :data="data"
    :word-detail-url="wordDetailUrl"
    :image-for-word="imageForWord"
    :fallback-letter="fallbackLetter"
  />
</template>
