<script setup>
import { ref, watch } from "vue";
import BooklearnerHero from "../components/BooklearnerHero.vue";
import BooklearnerRouteSections from "../components/BooklearnerRouteSections.vue";
import BooklearnerUploadModal from "../components/BooklearnerUploadModal.vue";

const props = defineProps([
  "route",
  "book",
  "go",
  "analyzeBookQuery",
  "analyzeBookFile",
  "saveBookAnalysis",
  "createBookWordList",
  "loadScienceDiscoveries",
  "loadScienceArticle"
]);

const uploadModalOpen = ref(false);

function openUploadModal() {
  uploadModalOpen.value = true;
}

function closeUploadModal() {
  uploadModalOpen.value = false;
  if (props.route.name === "booklearnerUpload") {
    props.go("/booklearner");
  }
}

watch(
  () => props.route.name,
  (routeName) => {
    if (routeName === "booklearnerUpload") {
      uploadModalOpen.value = true;
    }
  },
  { immediate: true },
);
</script>

<template>
  <section class="booklearner-page">
    <BooklearnerHero
      v-if="!['booklearnerDetail', 'booklearnerScience', 'booklearnerScienceHome'].includes(route.name)"
      :route="route"
      :book="book"
      :go="go"
      :open-upload-modal="openUploadModal"
    />

    <BooklearnerRouteSections
      :route="route"
      :book="book"
      :go="go"
      :analyze-book-query="analyzeBookQuery"
      :analyze-book-file="analyzeBookFile"
      :save-book-analysis="saveBookAnalysis"
      :create-book-word-list="createBookWordList"
      :load-science-discoveries="loadScienceDiscoveries"
      :load-science-article="loadScienceArticle"
    />

    <BooklearnerUploadModal
      v-if="uploadModalOpen"
      :book="book"
      :analyze-book-query="analyzeBookQuery"
      :analyze-book-file="analyzeBookFile"
      :save-book-analysis="saveBookAnalysis"
      :create-book-word-list="createBookWordList"
      @close="closeUploadModal"
    />
  </section>
</template>
