<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import VersionStamp from "./VersionStamp.vue";
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
  generateAiImage: {
    type: Function,
    required: true,
  },
});

const emit = defineEmits(["close", "select-image"]);

const previewUrl = ref("");
const isFinding = ref(false);
const isSavingUpload = ref(false);
const generatingAiModel = ref("");
const aiPreview = ref(null);
const aiCandidates = ref([]);
const aiNotice = ref("");
const aiTheme = ref("");
const aiStyle = ref("写实摄影");
const aiMeaning = ref("");

const aiImageModels = [
  { key: "wan27", label: "wan2.7-image-pro", provider: "dashscope", model: "wan2.7-image-pro" },
  { key: "qwen20", label: "qwen-image-2.0-pro", provider: "dashscope", model: "qwen-image-2.0-pro" },
  { key: "wan26", label: "wan2.6-t2i", provider: "dashscope", model: "wan2.6-t2i" },
];

const selectedFileName = computed(() => props.selectedImageFile?.name || "还没有选择图片");
const aiControls = computed(() => ({
  theme: aiTheme.value,
  style: aiStyle.value,
  meaning: aiMeaning.value,
}));

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

watch(
  () => props.word,
  (word) => {
    aiMeaning.value = word?.chinese_definition || "";
    aiCandidates.value = [];
    aiPreview.value = null;
    aiNotice.value = "";
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

async function generateAiCandidate(option) {
  if (generatingAiModel.value) return;
  generatingAiModel.value = option.key;
  aiNotice.value = "";
  try {
    const result = await props.generateAiImage(option, aiControls.value);
    const candidate = {
      ...option,
      imageUrl: result.image_url,
      model: result.model || option.model,
    };
    aiPreview.value = candidate;
    aiCandidates.value = [
      candidate,
      ...aiCandidates.value.filter((item) => item.key !== option.key),
    ];
    aiNotice.value = "已生成候选图，确认后保存。";
  } catch (error) {
    aiNotice.value = error.message || "AI 做图失败";
  } finally {
    generatingAiModel.value = "";
  }
}

async function generateAllAiCandidates() {
  if (generatingAiModel.value) return;
  aiCandidates.value = [];
  aiPreview.value = null;
  for (const option of aiImageModels) {
    await generateAiCandidate(option);
  }
}

async function saveAiPreview() {
  if (!aiPreview.value?.imageUrl) return;
  await props.chooseNetworkImage(aiPreview.value.imageUrl);
}
</script>

<template>
  <div class="word-image-manager-backdrop" role="dialog" aria-modal="true" aria-labelledby="wordImageManagerTitle">
    <section class="word-image-manager-modal">
      <header class="word-image-manager-heading">
        <div>
          <p class="section-kicker">Image</p>
          <h2 id="wordImageManagerTitle">图片管理</h2>
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
              <h3>AI 做图</h3>
            </div>
            <div class="ai-image-model-actions">
              <button
                v-for="option in aiImageModels"
                :key="option.key"
                class="secondary-button"
                type="button"
                :disabled="Boolean(generatingAiModel)"
                @click="generateAiCandidate(option)"
              >
                {{ generatingAiModel === option.key ? "生成中..." : option.label }}
              </button>
              <button
                class="secondary-button"
                type="button"
                :disabled="Boolean(generatingAiModel)"
                @click="generateAllAiCandidates"
              >
                三张对比
              </button>
            </div>
          </div>
          <div class="ai-image-form-grid">
            <label>
              <span>中文释义</span>
              <input v-model="aiMeaning" type="text" placeholder="苹果">
            </label>
            <label>
              <span>主题</span>
              <input v-model="aiTheme" type="text" placeholder="果园 / 厨房 / 教室">
            </label>
            <label>
              <span>风格</span>
              <select v-model="aiStyle">
                <option>写实摄影</option>
                <option>水彩</option>
                <option>卡通</option>
                <option>儿童绘本</option>
              </select>
            </label>
          </div>
          <div v-if="aiCandidates.length" class="ai-image-candidate-grid">
            <button
              v-for="candidate in aiCandidates"
              :key="candidate.key"
              class="ai-image-candidate"
              type="button"
              :class="{ selected: aiPreview?.key === candidate.key }"
              @click="aiPreview = candidate"
            >
              <img :src="candidate.imageUrl" :alt="`${word.word} ${candidate.label}`">
              <span>{{ candidate.label }}</span>
            </button>
          </div>
          <div v-if="aiPreview?.imageUrl" class="ai-image-preview">
            <img :src="aiPreview.imageUrl" :alt="`${word.word} AI 候选图`">
            <button class="challenge-button" type="button" @click="saveAiPreview">保存 AI 图片</button>
          </div>
          <p v-if="aiNotice" class="word-image-manager-empty">{{ aiNotice }}</p>
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
        <VersionStamp label="图片管理" />
      </div>
    </section>
  </div>
</template>
