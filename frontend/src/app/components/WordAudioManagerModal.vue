<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
  accent: {
    type: Object,
    required: true,
  },
  options: {
    type: Array,
    default: () => [],
  },
  fetchAudioOptions: {
    type: Function,
    required: true,
  },
  chooseAudio: {
    type: Function,
    required: true,
  },
  uploadAudio: {
    type: Function,
    required: true,
  },
});

const emit = defineEmits(["close"]);

const loadingOptions = ref(false);
const choosingUrl = ref("");
const savingUpload = ref(false);
const selectedFile = ref(null);
const previewUrl = ref("");
const notice = ref("");

const selectedFileName = computed(() => selectedFile.value?.name || "未选择音频文件");

function clearPreviewUrl() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
  previewUrl.value = "";
}

function selectUploadFile(event) {
  clearPreviewUrl();
  selectedFile.value = event.target.files?.[0] || null;
  if (selectedFile.value) previewUrl.value = URL.createObjectURL(selectedFile.value);
}

async function refreshOptions() {
  loadingOptions.value = true;
  notice.value = "";
  try {
    await props.fetchAudioOptions(props.accent.key);
    notice.value = "已更新可选音源";
  } catch (error) {
    notice.value = error.message || "获取音源失败";
  } finally {
    loadingOptions.value = false;
  }
}

async function chooseOption(url) {
  if (!url || choosingUrl.value) return;
  choosingUrl.value = url;
  notice.value = "";
  try {
    await props.chooseAudio(props.accent.key, url);
    emit("close");
  } catch (error) {
    notice.value = error.message || "保存音源失败";
  } finally {
    choosingUrl.value = "";
  }
}

async function saveUpload() {
  if (!selectedFile.value || savingUpload.value) return;
  savingUpload.value = true;
  notice.value = "";
  try {
    await props.uploadAudio(props.accent.key, selectedFile.value);
    emit("close");
  } catch (error) {
    notice.value = error.message || "上传音频失败";
  } finally {
    savingUpload.value = false;
  }
}

watch(() => props.accent.key, () => {
  selectedFile.value = null;
  notice.value = "";
  clearPreviewUrl();
});

onBeforeUnmount(clearPreviewUrl);
</script>

<template>
  <div class="audio-manager-backdrop" role="dialog" aria-modal="true">
    <section class="audio-manager-modal">
      <header class="audio-manager-heading">
        <div>
          <p class="section-kicker">{{ accent.label }}</p>
          <h2>音频管理</h2>
        </div>
        <button class="ghost-button compact-button" type="button" @click="emit('close')">关闭</button>
      </header>

      <div class="audio-manager-body">
        <section class="audio-manager-section">
          <div class="audio-manager-section-head">
            <div>
              <h3>重新获取</h3>
              <p>从多个词典音频源查找，试听后选择一个保存。</p>
            </div>
            <button class="secondary-button" type="button" :disabled="loadingOptions" @click="refreshOptions">
              {{ loadingOptions ? "获取中..." : "重新获取音源" }}
            </button>
          </div>
          <div v-if="options.length" class="audio-manager-options">
            <article v-for="option in options" :key="option.url" class="audio-manager-option">
              <strong>{{ option.label }}</strong>
              <audio controls :src="option.url" />
              <button
                class="secondary-button"
                type="button"
                :disabled="Boolean(choosingUrl)"
                @click="chooseOption(option.url)"
              >
                {{ choosingUrl === option.url ? "保存中..." : "保存这个" }}
              </button>
            </article>
          </div>
          <p v-else class="audio-manager-empty">还没有候选音频，点击重新获取音源。</p>
        </section>

        <section class="audio-manager-section">
          <div class="audio-manager-section-head">
            <div>
              <h3>录制音频</h3>
              <p>入口先保留，完整录音流程之后接入这个弹窗。</p>
            </div>
            <button class="secondary-button" type="button" disabled>之后做</button>
          </div>
        </section>

        <section class="audio-manager-section">
          <div class="audio-manager-section-head">
            <div>
              <h3>上传我的音频</h3>
              <p>选择音频文件后先预览，确认后保存为当前发音。</p>
            </div>
          </div>
          <label class="audio-upload-picker">
            <input type="file" accept="audio/*" @change="selectUploadFile">
            <span>选择音频</span>
            <strong>{{ selectedFileName }}</strong>
          </label>
          <audio v-if="previewUrl" controls :src="previewUrl" />
          <button
            class="challenge-button audio-manager-save"
            type="button"
            :disabled="!selectedFile || savingUpload"
            @click="saveUpload"
          >
            {{ savingUpload ? "保存中..." : "保存上传音频" }}
          </button>
        </section>

        <p v-if="notice" class="audio-manager-notice">{{ notice }}</p>
      </div>
    </section>
  </div>
</template>
