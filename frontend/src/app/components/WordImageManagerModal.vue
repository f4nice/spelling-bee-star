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
const isSavingReplacement = ref(false);
const generatingAiModels = ref([]);
const selectedReplacement = ref(null);
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
const replacementPreview = computed(() => {
  if (!selectedReplacement.value) return null;
  return selectedReplacement.value;
});
const aiControls = computed(() => ({
  theme: aiTheme.value,
  style: aiStyle.value,
  meaning: aiMeaning.value,
}));
const isGeneratingAi = computed(() => generatingAiModels.value.length > 0);

function isGeneratingModel(key) {
  return generatingAiModels.value.includes(key);
}

function beginGeneratingModel(key) {
  if (!isGeneratingModel(key)) {
    generatingAiModels.value = [...generatingAiModels.value, key];
  }
}

function endGeneratingModel(key) {
  generatingAiModels.value = generatingAiModels.value.filter((item) => item !== key);
}

function clearPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
  previewUrl.value = "";
}

watch(
  () => props.selectedImageFile,
  (file) => {
    clearPreview();
    if (file) {
      previewUrl.value = URL.createObjectURL(file);
      selectedReplacement.value = {
        type: "upload",
        imageUrl: previewUrl.value,
        label: "上传图片",
      };
    } else if (selectedReplacement.value?.type === "upload") {
      selectedReplacement.value = null;
    }
  },
  { immediate: true },
);

watch(
  () => props.word,
  (word) => {
    aiMeaning.value = word?.chinese_definition || "";
    aiCandidates.value = [];
    selectedReplacement.value = null;
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

async function saveReplacement() {
  if (!selectedReplacement.value) return;
  isSavingReplacement.value = true;
  try {
    if (selectedReplacement.value.type === "upload") {
      if (!props.selectedImageFile) return;
      await props.saveSelectedImage();
      return;
    }
    if (selectedReplacement.value.imageUrl) {
      await props.chooseNetworkImage(selectedReplacement.value.imageUrl);
    }
  } finally {
    isSavingReplacement.value = false;
  }
}

function selectAiCandidate(candidate) {
  selectedReplacement.value = {
    type: "ai",
    imageUrl: candidate.imageUrl,
    label: `AI 做图 · ${candidate.label}`,
    key: candidate.key,
  };
  aiNotice.value = "已放入准备替换，确认后点击保存。";
}

function selectNetworkCandidate(candidate) {
  selectedReplacement.value = {
    type: "network",
    imageUrl: candidate.url,
    label: "网络选图",
  };
}

async function generateAiCandidate(option) {
  if (isGeneratingModel(option.key)) return null;
  beginGeneratingModel(option.key);
  try {
    const result = await props.generateAiImage(option, aiControls.value);
    const candidate = {
      ...option,
      imageUrl: result.image_url,
      model: result.model || option.model,
    };
    aiCandidates.value = [
      candidate,
      ...aiCandidates.value.filter((item) => item.key !== option.key),
    ];
    aiNotice.value = "已生成候选图，点击图片放入准备替换。";
    return candidate;
  } catch (error) {
    aiNotice.value = error.message || "AI 做图失败";
    return null;
  } finally {
    endGeneratingModel(option.key);
  }
}

async function generateAllAiCandidates() {
  if (isGeneratingAi.value) return;
  aiCandidates.value = [];
  aiNotice.value = "三张图片生成中...";
  const results = await Promise.allSettled(aiImageModels.map((option) => generateAiCandidate(option)));
  const successCount = results.filter((result) => result.status === "fulfilled" && result.value).length;
  aiNotice.value = successCount ? `已生成 ${successCount} 张候选图，点击图片放入准备替换。` : "AI 做图失败";
}
</script>

<template>
  <div class="word-image-manager-backdrop" role="dialog" aria-modal="true" aria-labelledby="wordImageManagerTitle">
    <section class="word-image-manager-modal">
      <header class="word-image-manager-heading">
        <div>
          <p class="section-kicker">Image</p>
          <h2 id="wordImageManagerTitle">图片管理</h2>
        </div>
        <button class="secondary-button compact-button" type="button" @click="emit('close')">关闭</button>
      </header>

      <div class="word-image-manager-body">
        <section class="word-image-manager-section word-image-compare-section">
          <div class="word-image-compare-card">
            <div>
              <h3>当前图片</h3>
              <p>{{ word.word }}</p>
            </div>
            <img v-if="imageUrl" class="word-image-manager-preview" :src="imageUrl" :alt="word.word">
            <div v-else class="image-fallback word-image-manager-preview">{{ word.word.slice(0, 1).toUpperCase() }}</div>
          </div>
          <div class="word-image-compare-card is-replacement">
            <div>
              <h3>准备替换</h3>
              <p>{{ replacementPreview?.label || "等待选择" }}</p>
            </div>
            <img
              v-if="replacementPreview?.imageUrl"
              class="word-image-manager-preview"
              :src="replacementPreview.imageUrl"
              :alt="`${word.word} 准备替换图片`"
            >
            <div v-else class="word-image-manager-preview word-image-replacement-empty">等待选择图片</div>
          </div>
        </section>

        <div class="word-image-save-bar">
          <button
            class="challenge-button word-image-save-replacement"
            type="button"
            :disabled="!replacementPreview || isSavingReplacement"
            @click="saveReplacement"
          >
            {{ isSavingReplacement ? "保存中..." : "保存" }}
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
              @change="emit('select-image', $event.target.files[0] || null)"
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
            <div class="ai-image-model-actions">
              <button
                v-for="option in aiImageModels"
                :key="option.key"
                class="secondary-button"
                type="button"
                :disabled="isGeneratingModel(option.key)"
                @click="generateAiCandidate(option)"
              >
                {{ isGeneratingModel(option.key) ? "生成中..." : option.model }}
              </button>
              <button
                class="secondary-button"
                type="button"
                :disabled="isGeneratingAi"
                @click="generateAllAiCandidates"
              >
                {{ isGeneratingAi ? "生成中..." : "三张对比" }}
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
              :class="{ selected: selectedReplacement?.type === 'ai' && selectedReplacement?.key === candidate.key }"
              @click="selectAiCandidate(candidate)"
            >
              <img :src="candidate.imageUrl" :alt="`${word.word} ${candidate.label}`">
              <span>{{ candidate.model }}</span>
            </button>
          </div>
          <p v-if="aiNotice" class="word-image-manager-empty">{{ aiNotice }}</p>
        </section>

        <section class="word-image-manager-section">
          <div class="word-image-manager-section-head">
            <div>
              <h3>网络找图</h3>
            </div>
            <button class="secondary-button" type="button" :disabled="isFinding" @click="runFindImages">
              {{ isFinding ? "查找中..." : "网络找图" }}
            </button>
          </div>
          <WordImageCandidateGrid
            v-if="imageCandidates.length"
            :word="word"
            :image-candidates="imageCandidates"
            :select-image-candidate="selectNetworkCandidate"
          />
          <p v-else class="word-image-manager-empty">暂无候选图</p>
        </section>
        <VersionStamp label="图片管理" />
      </div>
    </section>
  </div>
</template>
