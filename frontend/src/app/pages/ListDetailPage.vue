<script setup>
import ListDetailHeader from "../components/ListDetailHeader.vue";
import ListImageSyncPanel from "../components/ListImageSyncPanel.vue";
import WordCard from "../components/WordCard.vue";

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
  <section class="word-grid">
    <WordCard
      v-for="(word, index) in data.words"
      :key="word.id"
      :word="word"
      :index="index"
      :href="wordDetailUrl(word, data.word_list.id)"
      :image-url="imageForWord(word)"
      :fallback-letter="fallbackLetter(word)"
    />
  </section>
</template>
