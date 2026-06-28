<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import VersionStamp from "./VersionStamp.vue";

const props = defineProps({
  analysisId: {
    type: Number,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
  author: {
    type: String,
    default: "",
  },
  coverUrl: {
    type: String,
    default: "",
  },
  uploadBookCover: {
    type: Function,
    required: true,
  },
  generateBookAiCover: {
    type: Function,
    required: true,
  },
});

const emit = defineEmits(["close"]);

const selectedFile = ref(null);
const previewUrl = ref("");
const replacementPreview = ref(null);
const isSavingReplacement = ref(false);
const isGeneratingAi = ref(false);
const notice = ref("");
const aiTheme = ref("");
const aiStyle = ref("书籍封面插画");
const aiModel = ref("wan2.7-image-pro");

const selectedFileName = computed(() => selectedFile.value?.name || "还没有选择图片");
const fallbackLetter = computed(() => (props.title || "B").slice(0, 1).toUpperCase());

const aiImageModels = [
  "wan2.7-image-pro",
  "qwen-image-2.0-pro",
  "wan2.6-t2i",
];

function clearPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
  previewUrl.value = "";
}

function selectImageFile(file) {
  clearPreview();
  selectedFile.value = file || null;
  notice.value = "";
  if (!file) {
    replacementPreview.value = null;
    return;
  }
  previewUrl.value = URL.createObjectURL(file);
  replacementPreview.value = {
    type: "upload",
    imageUrl: previewUrl.value,
    label: "上传图片",
  };
}

watch(
  () => props.coverUrl,
  () => {
    if (replacementPreview.value?.type === "saved") {
      replacementPreview.value = null;
    }
  },
);

onBeforeUnmount(clearPreview);

async function saveReplacement() {
  if (!selectedFile.value) return;
  isSavingReplacement.value = true;
  notice.value = "";
  try {
    const result = await props.uploadBookCover(props.analysisId, selectedFile.value);
    selectedFile.value = null;
    replacementPreview.value = result?.coverUrl
      ? { type: "saved", imageUrl: result.coverUrl, label: "已保存封面" }
      : null;
    notice.value = "封面图片已保存。";
  } catch (error) {
    notice.value = error.message || "封面图片保存失败。";
  } finally {
    isSavingReplacement.value = false;
  }
}

async function generateAiCover() {
  if (isGeneratingAi.value) return;
  isGeneratingAi.value = true;
  notice.value = "AI 封面生成中...";
  try {
    const result = await props.generateBookAiCover(props.analysisId, {
      model: aiModel.value,
      theme: aiTheme.value,
      style: aiStyle.value,
    });
    replacementPreview.value = result?.coverUrl
      ? { type: "saved", imageUrl: result.coverUrl, label: `AI 封面 · ${result.model || aiModel.value}` }
      : null;
    notice.value = "AI 封面已保存。";
  } catch (error) {
    notice.value = error.message || "AI 封面生成失败。";
  } finally {
    isGeneratingAi.value = false;
  }
}
</script>

<template>
  <div class="word-image-manager-backdrop" role="dialog" aria-modal="true" aria-labelledby="bookCoverManagerTitle">
    <section class="word-image-manager-modal book-cover-manager-modal">
      <header class="word-image-manager-heading">
        <div>
          <p class="section-kicker">Book Cover</p>
          <h2 id="bookCoverManagerTitle">图片管理</h2>
          <p>{{ title }}</p>
        </div>
        <button class="secondary-button compact-button" type="button" @click="emit('close')">关闭</button>
      </header>

      <div class="word-image-manager-body">
        <section class="word-image-manager-section word-image-compare-section book-cover-compare-section">
          <div class="word-image-compare-card">
            <div>
              <h3>当前封面</h3>
              <p>{{ author || "作者未记录" }}</p>
            </div>
            <img v-if="coverUrl" class="word-image-manager-preview book-cover-manager-preview" :src="coverUrl" :alt="title">
            <div v-else class="image-fallback word-image-manager-preview book-cover-manager-preview">
              {{ fallbackLetter }}
            </div>
          </div>
          <div class="word-image-compare-card is-replacement">
            <div>
              <h3>准备替换</h3>
              <p>{{ replacementPreview?.label || "等待选择" }}</p>
            </div>
            <img
              v-if="replacementPreview?.imageUrl"
              class="word-image-manager-preview book-cover-manager-preview"
              :src="replacementPreview.imageUrl"
              :alt="`${title} 准备替换封面`"
            >
            <div v-else class="word-image-manager-preview book-cover-manager-preview word-image-replacement-empty">
              等待选择图片
            </div>
          </div>
        </section>

        <div class="word-image-save-bar">
          <button
            class="challenge-button word-image-save-replacement"
            type="button"
            :disabled="!selectedFile || isSavingReplacement"
            @click="saveReplacement"
          >
            {{ isSavingReplacement ? "保存中..." : "保存上传图片" }}
          </button>
        </div>

        <section class="word-image-manager-section">
          <div class="word-image-manager-section-head">
            <div>
              <h3>上传图片</h3>
            </div>
          </div>
          <label class="image-upload-picker">
            <input
              type="file"
              accept="image/*"
              @change="selectImageFile($event.target.files[0] || null)"
            >
            <span>选择图片</span>
            <strong>{{ selectedFileName }}</strong>
          </label>
        </section>

        <section class="word-image-manager-section">
          <div class="word-image-manager-section-head">
            <div>
              <h3>AI 做图</h3>
            </div>
            <button class="challenge-button ai-image-generate-button" type="button" :disabled="isGeneratingAi" @click="generateAiCover">
              {{ isGeneratingAi ? "生成中..." : "生成封面" }}
            </button>
          </div>
          <div class="ai-image-form-grid">
            <label>
              <span>模型</span>
              <select v-model="aiModel">
                <option v-for="model in aiImageModels" :key="model">{{ model }}</option>
              </select>
            </label>
            <label>
              <span>主题</span>
              <input v-model="aiTheme" type="text" placeholder="可选：城市、餐桌、绿色灯光">
            </label>
            <label>
              <span>风格</span>
              <select v-model="aiStyle">
                <option>书籍封面插画</option>
                <option>儿童绘本</option>
                <option>复古文学</option>
                <option>极简海报</option>
              </select>
            </label>
          </div>
          <p v-if="notice" class="word-image-manager-empty">{{ notice }}</p>
        </section>
        <VersionStamp label="书籍图片管理" />
      </div>
    </section>
  </div>
</template>
