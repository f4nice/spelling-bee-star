<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import VersionStamp from "./VersionStamp.vue";

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
  generateAiAudio: {
    type: Function,
    required: true,
  },
});

const emit = defineEmits(["close"]);

const loadingOptions = ref(false);
const savingSelection = ref(false);
const generatingGender = ref("");
const selectedFile = ref(null);
const previewUrl = ref("");
const pendingAudio = ref(null);
const previewAudio = ref(null);
const notice = ref("");

const selectedFileName = computed(() => selectedFile.value?.name || "未选择音频文件");
const aiButtonLabel = computed(() => {
  const accentName = props.accent.key === "gb" ? "英式" : "美式";
  return `生成${accentName} AI 朗读`;
});
const pendingAudioLabel = computed(() => pendingAudio.value?.label || "还没有选择试听音频");
const canSavePendingAudio = computed(() => Boolean(pendingAudio.value?.url || pendingAudio.value?.file));

function clearPreviewUrl() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
  previewUrl.value = "";
}

function setPendingAudio(source) {
  if (source.type !== "upload") clearPreviewUrl();
  pendingAudio.value = source;
}

async function playPendingAudio() {
  await nextTick();
  const player = previewAudio.value;
  if (!player) return false;
  try {
    player.currentTime = 0;
    await player.play();
    return true;
  } catch {
    return false;
  }
}

function selectUploadFile(event) {
  clearPreviewUrl();
  selectedFile.value = event.target.files?.[0] || null;
  if (selectedFile.value) {
    previewUrl.value = URL.createObjectURL(selectedFile.value);
    setPendingAudio({
      type: "upload",
      file: selectedFile.value,
      url: previewUrl.value,
      label: `上传音频 · ${selectedFile.value.name}`,
    });
    notice.value = "已放入上方播放器，可以试听后保存。";
  }
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

function previewOption(option) {
  if (!option?.url) return;
  setPendingAudio({
    type: "url",
    url: option.url,
    label: option.label || "候选音源",
  });
  notice.value = "已放入上方播放器，可以试听后保存。";
}

async function saveCurrentAudio() {
  if (!pendingAudio.value || savingSelection.value) return;
  savingSelection.value = true;
  notice.value = "";
  try {
    if (pendingAudio.value.type === "upload") {
      await props.uploadAudio(props.accent.key, pendingAudio.value.file);
    } else {
      await props.chooseAudio(props.accent.key, pendingAudio.value.url);
    }
    emit("close");
  } catch (error) {
    notice.value = error.message || "保存音频失败";
  } finally {
    savingSelection.value = false;
  }
}

async function generateAiSource(voiceGender) {
  if (generatingGender.value) return;
  generatingGender.value = voiceGender;
  notice.value = "";
  try {
    const result = await props.generateAiAudio(props.accent.key, voiceGender);
    const voiceLabel = voiceGender === "male" ? "男声" : "女声";
    setPendingAudio({
      type: "url",
      url: result.audio_url,
      label: `${aiButtonLabel.value} · ${voiceLabel}`,
    });
    const played = await playPendingAudio();
    notice.value = played
      ? "AI 音频已生成并自动播放，确认后保存。"
      : "AI 音频已生成，浏览器未自动播放时可点上方播放器试听，确认后保存。";
  } catch (error) {
    notice.value = error.message || "AI 朗读生成失败";
  } finally {
    generatingGender.value = "";
  }
}

watch(() => props.accent.key, () => {
  selectedFile.value = null;
  pendingAudio.value = null;
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
        <section class="audio-manager-section audio-manager-preview">
          <div class="audio-manager-section-head">
            <div>
              <h3>当前试听音频</h3>
              <p>{{ pendingAudioLabel }}</p>
            </div>
            <button
              class="challenge-button"
              type="button"
              :disabled="!canSavePendingAudio || savingSelection"
              @click="saveCurrentAudio"
            >
              {{ savingSelection ? "保存中..." : "保存当前音频" }}
            </button>
          </div>
          <audio v-if="pendingAudio?.url" ref="previewAudio" controls :src="pendingAudio.url" />
          <p v-else class="audio-manager-empty">先从下方选择、上传或生成一个音频。</p>
        </section>

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
              <button
                class="secondary-button"
                type="button"
                @click="previewOption(option)"
              >
                放入试听
              </button>
            </article>
          </div>
          <p v-else class="audio-manager-empty">还没有候选音频，点击重新获取音源。</p>
        </section>

        <section class="audio-manager-section">
          <div class="audio-manager-section-head">
            <div>
              <h3>AI 朗读</h3>
              <p>生成后会保存为当前单词的{{ accent.label }}音频，以后直接用播放器播放。</p>
            </div>
            <div class="audio-manager-button-group">
              <button
                class="secondary-button"
                type="button"
                :disabled="Boolean(generatingGender)"
                @click="generateAiSource('female')"
              >
                {{ generatingGender === "female" ? "生成中..." : `${aiButtonLabel} · 女声` }}
              </button>
              <button
                class="secondary-button"
                type="button"
                :disabled="Boolean(generatingGender)"
                @click="generateAiSource('male')"
              >
                {{ generatingGender === "male" ? "生成中..." : `${aiButtonLabel} · 男声` }}
              </button>
            </div>
          </div>
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
        </section>

        <p v-if="notice" class="audio-manager-notice">{{ notice }}</p>
        <VersionStamp label="音频管理" />
      </div>
    </section>
  </div>
</template>
