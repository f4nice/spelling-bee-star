<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import WordImageCandidateGrid from "./WordImageCandidateGrid.vue";

const props = defineProps({
  word: {
    type: Object,
    required: true,
  },
  imageUrl: {
    type: String,
    default: "",
  },
  selectedImageFile: {
    type: Object,
    default: null,
  },
  imageCandidates: {
    type: Array,
    required: true,
  },
  findImages: {
    type: Function,
    required: true,
  },
  saveSelectedImage: {
    type: Function,
    required: true,
  },
  chooseNetworkImage: {
    type: Function,
    required: true,
  },
});

const emit = defineEmits(["close", "select-image"]);

const previewUrl = ref("");
const isFinding = ref(false);
const isSavingUpload = ref(false);

const selectedFileName = computed(() => props.selectedImageFile?.name || "还没有选择图片");

function clearPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
  previewUrl.value = "";
}

watch(
  () => props.selectedImageFile,
  (file) => {
    clearPreview();
    if (file) previewUrl.value = URL.createObjectURL(file);
  },
  { immediate: true },
);

onBeforeUnmount(clearPreview);

async function runFindImages() {
  isFinding.value = true;
  try {
    await props.findImages();
  } finally {
    isFinding.value = false;
  }
}

async function saveUpload() {
  if (!props.selectedImageFile) return;
  isSavingUpload.value = true;
  try {
    await props.saveSelectedImage();
  } finally {
    isSavingUpload.value = false;
  }
}
</script>

<template>
  <div class="word-image-manager-backdrop" role="dialog" aria-modal="true" aria-labelledby="wordImageManagerTitle">
    <section class="word-image-manager-modal">
      <header class="word-image-manager-heading">
        <div>
          <p class="section-kicker">Image</p>
          <h2 id="wordImageManagerTitle">修改图片</h2>
          <p>上传自己的图片，或从网络候选图里选择一张保存为当前单词图片。</p>
        </div>
        <button class="secondary-button compact-button" type="button" @click="emit('close')">关闭</button>
      </header>

      <div class="word-image-manager-body">
        <section class="word-image-manager-section">
          <div>
            <h3>当前图片</h3>
            <p>{{ word.word }}</p>
          </div>
          <img v-if="imageUrl" class="word-image-manager-preview" :src="imageUrl" :alt="word.word">
          <div v-else class="image-fallback word-image-manager-preview">{{ word.word.slice(0, 1).toUpperCase() }}</div>
        </section>

        <section class="word-image-manager-section">
          <div class="word-image-manager-section-head">
            <div>
              <h3>上传图片</h3>
              <p>先选择图片预览，确认后点击保存。</p>
            </div>
          </div>
          <label class="image-upload-picker">
            <input
              type="file"
              accept="image/*"
              @change="emit('select-image', $event.target.files[0] || null)"
            >
            <span>选择图片</span>
            <strong>{{ selectedFileName }}</strong>
          </label>
          <img v-if="previewUrl" class="word-image-upload-preview" :src="previewUrl" alt="上传预览">
          <button
            class="challenge-button"
            type="button"
            :disabled="!selectedImageFile || isSavingUpload"
            @click="saveUpload"
          >
            {{ isSavingUpload ? "保存中..." : "保存上传图片" }}
          </button>
        </section>

        <section class="word-image-manager-section">
          <div class="word-image-manager-section-head">
            <div>
              <h3>网络找图</h3>
              <p>获取候选图后，点击喜欢的图片即可保存。</p>
            </div>
            <button class="secondary-button" type="button" :disabled="isFinding" @click="runFindImages">
              {{ isFinding ? "查找中..." : "网络找图" }}
            </button>
          </div>
          <WordImageCandidateGrid
            v-if="imageCandidates.length"
            :word="word"
            :image-candidates="imageCandidates"
            :choose-network-image="chooseNetworkImage"
          />
          <p v-else class="word-image-manager-empty">还没有候选图片，点击网络找图开始查找。</p>
        </section>
      </div>
    </section>
  </div>
</template>
