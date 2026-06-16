<script setup>
import ListDetailHeader from "../components/ListDetailHeader.vue";
import ListImageSyncPanel from "../components/ListImageSyncPanel.vue";
import WordCard from "../components/WordCard.vue";

defineProps([
  "data",
  "renameList",
  "syncListImages",
  "wordVueUrl",
  "imageForWord",
  "fallbackLetter"
]);
</script>

<template>
  <ListDetailHeader :data="data" :rename-list="renameList" />
  <ListImageSyncPanel :sync-job="data.sync_job" :sync-list-images="syncListImages" />
  <section class="word-grid">
    <WordCard
      v-for="(word, index) in data.words"
      :key="word.id"
      :word="word"
      :index="index"
      :href="wordVueUrl(word, data.word_list.id)"
      :image-for-word="imageForWord"
      :fallback-letter="fallbackLetter"
    />
  </section>
</template>
