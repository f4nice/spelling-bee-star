<script setup>
import { computed, ref } from "vue";
import { useSelectedWordImage } from "../composables/useSelectedWordImage.js";
import { wordMediaPanelProps } from "../props/wordMediaPanelProps.js";
import { wordAudioAccents } from "../wordAudioAccents.js";
import WordAudioManagerModal from "./WordAudioManagerModal.vue";
import WordImageFrame from "./WordImageFrame.vue";
import WordImageManagerModal from "./WordImageManagerModal.vue";

const props = defineProps(wordMediaPanelProps);
const isImageModalOpen = ref(false);
const isAudioModalOpen = ref(false);
const selectedAudioAccentKey = ref("us");
const selectedAudioAccent = computed(() => wordAudioAccents.find((accent) => accent.key === selectedAudioAccentKey.value) || wordAudioAccents[0]);
const selectedAudioOptions = computed(() => props.audioOptions?.[selectedAudioAccent.value.key] || []);

const { selectedImageFile, selectImageFile, saveSelectedImage } = useSelectedWordImage({
  uploadWordImage: props.uploadWordImage,
});

async function saveUploadedImage() {
  await saveSelectedImage();
  isImageModalOpen.value = false;
}

async function chooseNetworkImageAndClose(url) {
  await props.chooseNetworkImage(url);
  isImageModalOpen.value = false;
}

async function generateAiImage(option, controls = {}) {
  if (typeof props.generateAiImage !== "function") {
    throw new Error("AI 做图方法未加载，请刷新页面后重试。");
  }
  return props.generateAiImage(option, controls);
}

function openAudioModal() {
  selectedAudioAccentKey.value = "us";
  isAudioModalOpen.value = true;
}
</script>

<template>
  <aside class="panel media-panel">
    <WordImageFrame :word="data.word" :image-url="imageForWord(data.word)" />

    <div v-if="data.can_edit" class="word-media-action-row">
      <button
        class="secondary-button media-manager-button image-manager-trigger"
        type="button"
        @click="isImageModalOpen = true"
      >
        图片管理
      </button>
      <button
        class="secondary-button media-manager-button audio-manager-trigger"
        type="button"
        @click="openAudioModal"
      >
        音频管理
      </button>
    </div>

    <WordImageManagerModal
      v-if="isImageModalOpen"
      :word="data.word"
      :image-url="imageForWord(data.word)"
      :selected-image-file="selectedImageFile"
      :image-candidates="imageCandidates"
      :find-images="findImages"
      :save-selected-image="saveUploadedImage"
      :choose-network-image="chooseNetworkImageAndClose"
      :generate-ai-image="generateAiImage"
      @select-image="selectImageFile"
      @close="isImageModalOpen = false"
    />

    <WordAudioManagerModal
      v-if="isAudioModalOpen"
      :accent="selectedAudioAccent"
      :accents="wordAudioAccents"
      :selected-accent-key="selectedAudioAccentKey"
      :data="data"
      :options="selectedAudioOptions"
      :fetch-audio-options="fetchAudioOptions"
      :choose-audio="chooseAudio"
      :upload-audio="uploadAudio"
      :generate-ai-audio="generateAiAudio"
      @change-accent="selectedAudioAccentKey = $event"
      @close="isAudioModalOpen = false"
    />
  </aside>
</template>
