<script setup>
import { ref } from "vue";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  imageCandidates: {
    type: Array,
    required: true,
  },
  imageForWord: {
    type: Function,
    required: true,
  },
  uploadWordImage: {
    type: Function,
    required: true,
  },
  findImages: {
    type: Function,
    required: true,
  },
  chooseNetworkImage: {
    type: Function,
    required: true,
  },
});

const selectedImageFile = ref(null);

async function saveSelectedImage() {
  if (!selectedImageFile.value) return;
  await props.uploadWordImage(selectedImageFile.value);
  selectedImageFile.value = null;
}
</script>

<template>
  <aside class="panel media-panel">
    <div class="word-image-frame">
      <img v-if="imageForWord(data.word)" :src="imageForWord(data.word)" :alt="data.word.word">
      <div v-else class="image-fallback">{{ data.word.word.slice(0, 1).toUpperCase() }}</div>
    </div>

    <div v-if="data.can_edit" class="media-tools" role="group" aria-label="单词图片工具">
      <label>
        上传图片
        <input
          type="file"
          accept="image/*"
          @change="selectedImageFile = $event.target.files[0] || null"
        >
      </label>
      <button
        type="button"
        class="secondary-button"
        :disabled="!selectedImageFile"
        @click="saveSelectedImage"
      >
        保存图片
      </button>
      <button type="button" class="secondary-button" @click="findImages">网络找图</button>
    </div>

    <div v-if="imageCandidates.length" class="image-picker-grid inline-image-grid">
      <button
        v-for="(item, index) in imageCandidates"
        :key="item.url || index"
        type="button"
        class="image-candidate-button"
        @click="chooseNetworkImage(item.url)"
      >
        <img :src="item.url" :alt="`${data.word.word} 候选图 ${index + 1}`">
      </button>
    </div>
  </aside>
</template>
