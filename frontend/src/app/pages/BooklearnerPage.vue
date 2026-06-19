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
  "analyzeBookText",
  "analyzeBookFile",
  "saveBookAnalysis",
  "createBookWordList"
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
      :analyze-book-text="analyzeBookText"
      :analyze-book-file="analyzeBookFile"
      :save-book-analysis="saveBookAnalysis"
      :create-book-word-list="createBookWordList"
    />

    <BooklearnerUploadModal
      v-if="uploadModalOpen"
      :book="book"
      :analyze-book-query="analyzeBookQuery"
      :analyze-book-text="analyzeBookText"
      :analyze-book-file="analyzeBookFile"
      :save-book-analysis="saveBookAnalysis"
      :create-book-word-list="createBookWordList"
      @close="closeUploadModal"
    />
  </section>
</template>
