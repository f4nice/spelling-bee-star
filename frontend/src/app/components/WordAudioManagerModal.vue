<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { inferAudioSourceMeta, sourceText } from "../mediaSourceLabels.js";
import VersionStamp from "./VersionStamp.vue";

const props = defineProps({
  accent: {
    type: Object,
    required: true,
  },
  accents: {
    type: Array,
    default: () => [],
  },
  selectedAccentKey: {
    type: String,
    default: "",
  },
  data: {
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
  generateDefinitionAudio: {
    type: Function,
    default: null,
  },
  generateExampleAudio: {
    type: Function,
    default: null,
  },
});

const emit = defineEmits(["change-accent", "close"]);

const activeTargetKey = ref(props.selectedAccentKey || props.accent.key || "us");
const loadingOptions = ref(false);
const loadingSpbOptions = ref(false);
const savingSelection = ref(false);
const generatingKey = ref("");
const selectedFile = ref(null);
const previewUrl = ref("");
const pendingAudio = ref(null);
const previewAudio = ref(null);
const notice = ref("");

const selectedFileName = computed(() => selectedFile.value?.name || "未选择音频文件");
const word = computed(() => props.data.word || {});
const audioSources = computed(() => props.data.audio_sources || {});
const mediaSources = computed(() => props.data.media_sources || {});
const audioMediaSources = computed(() => mediaSources.value.audio || {});
const phoneticText = computed(() => String(word.value.phonetic || "").trim().replace(/^\/+|\/+$/g, "").trim());
const hasPhoneticText = computed(() => Boolean(phoneticText.value));

function isLocalAudioUrl(url) {
  return typeof url === "string" && url.startsWith("/media/audio/");
}

function wordAudioUrl(accentKey) {
  if (accentKey === "gb") return audioSources.value.gb || word.value.british_audio_url || "";
  return audioSources.value.us || word.value.american_audio_url || "";
}

function targetStatus(url) {
  if (!url) return "待处理";
  return isLocalAudioUrl(url) ? "服务器已有" : "可播放";
}

function audioMetaFor(key, url) {
  return inferAudioSourceMeta(audioMediaSources.value[key] || {}, url);
}

function optionSourceMeta(option) {
  return inferAudioSourceMeta(option?.source_meta || { source: option?.source || option?.label || "" }, option?.url || "");
}

function displaySource(meta) {
  return sourceText(meta);
}

function resultSourceMeta(result, key, fallbackSource = "", fallbackUrl = "") {
  return inferAudioSourceMeta(
    result?.source_meta || result?.media_sources?.audio?.[key] || { source: result?.source || fallbackSource },
    result?.audio_url || fallbackUrl || "",
  );
}

function applyMediaSources(result) {
  if (result?.media_sources) props.data.media_sources = result.media_sources;
}

const wordTargets = computed(() => {
  const accents = props.accents.length ? props.accents : [{ key: "us", label: "美式发音" }, { key: "gb", label: "英式发音" }];
  return accents.map((item) => {
    const currentUrl = wordAudioUrl(item.key);
    return {
      key: item.key,
      type: "word",
      label: item.key === "gb" ? "英式单词" : "美式单词",
      subtitle: item.key === "gb" ? "只处理英式单词发音" : "只处理美式单词发音",
      currentUrl,
      sourceMeta: audioMetaFor(item.key, currentUrl),
      status: targetStatus(currentUrl),
    };
  });
});

const fieldTargets = computed(() => [
  {
    key: "definition",
    type: "definition",
    label: "英文定义",
    subtitle: "朗读英文定义，不影响单词发音",
    currentUrl: word.value.english_definition_audio_url || "",
    text: word.value.english_definition || "",
    sourceMeta: audioMetaFor("definition", word.value.english_definition_audio_url || ""),
    status: targetStatus(word.value.english_definition_audio_url || ""),
  },
  {
    key: "example",
    type: "example",
    label: "英文例句",
    subtitle: "优先复用 SPB 小程序例句音频",
    currentUrl: word.value.english_example_audio_url || "",
    text: word.value.english_example || "",
    sourceMeta: audioMetaFor("example", word.value.english_example_audio_url || ""),
    status: targetStatus(word.value.english_example_audio_url || ""),
  },
]);

const audioTargets = computed(() => [...wordTargets.value, ...fieldTargets.value]);
const activeTarget = computed(() => audioTargets.value.find((item) => item.key === activeTargetKey.value) || audioTargets.value[0]);
const isWordTarget = computed(() => activeTarget.value?.type === "word");
const isDefinitionTarget = computed(() => activeTarget.value?.type === "definition");
const isExampleTarget = computed(() => activeTarget.value?.type === "example");
const accentName = computed(() => (activeTarget.value?.key === "gb" ? "英式" : "美式"));
const activeOptions = computed(() => (isWordTarget.value ? props.options : []));
const currentAudioUrl = computed(() => pendingAudio.value?.url || activeTarget.value?.currentUrl || "");
const currentAudioLabel = computed(() => pendingAudio.value?.label || (activeTarget.value?.currentUrl ? `${activeTarget.value.label} · 当前音频` : "还没有音频"));
const currentAudioSourceMeta = computed(() => pendingAudio.value?.sourceMeta || activeTarget.value?.sourceMeta || inferAudioSourceMeta({}, currentAudioUrl.value));
const currentAudioSourceText = computed(() => displaySource(currentAudioSourceMeta.value));
const canSavePendingAudio = computed(() => isWordTarget.value && Boolean(pendingAudio.value?.url || pendingAudio.value?.file));
const canUseUpload = computed(() => isWordTarget.value);
const canUseWordAi = computed(() => isWordTarget.value);
const canUseDictionary = computed(() => isWordTarget.value);
const fieldText = computed(() => String(activeTarget.value?.text || "").trim());

function aiButtonLabel(textMode = "word") {
  return `生成${accentName.value} AI朗读${textMode === "phonetic" ? "音标" : "单词"}`;
}

function aiButtonText(textMode, voiceGender) {
  const currentKey = `${textMode}:${voiceGender}`;
  const voiceLabel = voiceGender === "male" ? "男声" : "女声";
  return generatingKey.value === currentKey ? "生成中..." : `${aiButtonLabel(textMode)} · ${voiceLabel}`;
}

function canGenerateAi(textMode) {
  return !generatingKey.value && canUseWordAi.value && (textMode !== "phonetic" || hasPhoneticText.value);
}

const phoneticRowHint = computed(() => {
  if (hasPhoneticText.value) return `当前音标 /${phoneticText.value}/`;
  return "还没有音标，先双击单词下方音标补充后再生成。";
});

const fieldGenerateText = computed(() => {
  if (isDefinitionTarget.value) return generatingKey.value === "definition" ? "生成中..." : "生成英文定义音频";
  return generatingKey.value === "example" ? "处理中..." : "获取/生成英文例句音频";
});

const fieldSpbSyncText = computed(() => {
  if (generatingKey.value === "definition:spb") return "同步中...";
  if (generatingKey.value === "example:spb") return "同步中...";
  return "同步小程序音频";
});

const canGenerateFieldAudio = computed(() => {
  if (generatingKey.value || !fieldText.value) return false;
  if (isDefinitionTarget.value) return typeof props.generateDefinitionAudio === "function";
  if (isExampleTarget.value) return typeof props.generateExampleAudio === "function";
  return false;
});

const canSyncFieldFromSpb = computed(() => {
  if (generatingKey.value || !fieldText.value) return false;
  if (isDefinitionTarget.value) return typeof props.generateDefinitionAudio === "function";
  if (isExampleTarget.value) return typeof props.generateExampleAudio === "function";
  return false;
});

function clearPreviewUrl() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
  previewUrl.value = "";
}

function resetPendingAudio() {
  selectedFile.value = null;
  pendingAudio.value = null;
  notice.value = "";
  clearPreviewUrl();
}

function setPendingAudio(source) {
  if (source.type !== "upload") clearPreviewUrl();
  pendingAudio.value = source;
}

function selectTarget(key) {
  activeTargetKey.value = key;
  resetPendingAudio();
  if (key === "us" || key === "gb") emit("change-accent", key);
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
  if (!canUseUpload.value) return;
  clearPreviewUrl();
  selectedFile.value = event.target.files?.[0] || null;
  if (selectedFile.value) {
    previewUrl.value = URL.createObjectURL(selectedFile.value);
    setPendingAudio({
      type: "upload",
      file: selectedFile.value,
      url: previewUrl.value,
      label: `上传音频 · ${selectedFile.value.name}`,
      sourceMeta: inferAudioSourceMeta({ source: "upload" }, previewUrl.value),
    });
    notice.value = "已放入上方播放器，可以试听后保存。";
  }
}

async function refreshOptions() {
  if (!canUseDictionary.value) return;
  loadingOptions.value = true;
  notice.value = "";
  try {
    await props.fetchAudioOptions(activeTarget.value.key, "dictionary");
    notice.value = "已更新可选音源";
  } catch (error) {
    notice.value = error.message || "获取音源失败";
  } finally {
    loadingOptions.value = false;
  }
}

async function refreshSpbOptions() {
  if (!canUseDictionary.value) return;
  loadingSpbOptions.value = true;
  notice.value = "";
  try {
    await props.fetchAudioOptions(activeTarget.value.key, "spb");
    notice.value = "已获取小程序单词音频候选，试听后可以保存。";
  } catch (error) {
    notice.value = error.message || "获取小程序音频失败";
  } finally {
    loadingSpbOptions.value = false;
  }
}

function previewOption(option) {
  if (!option?.url) return;
  setPendingAudio({
    type: "url",
    url: option.url,
    label: option.label || "候选音源",
    sourceMeta: optionSourceMeta(option),
  });
  notice.value = "已放入上方播放器，可以试听后保存。";
}

async function saveCurrentAudio() {
  if (!canSavePendingAudio.value || savingSelection.value) return;
  savingSelection.value = true;
  notice.value = "";
  try {
    let result = null;
    if (pendingAudio.value.type === "upload") {
      result = await props.uploadAudio(activeTarget.value.key, pendingAudio.value.file);
    } else {
      result = await props.chooseAudio(activeTarget.value.key, pendingAudio.value.url);
    }
    applyMediaSources(result);
    emit("close");
  } catch (error) {
    notice.value = error.message || "保存音频失败";
  } finally {
    savingSelection.value = false;
  }
}

async function generateAiSource(textMode, voiceGender) {
  if (!canGenerateAi(textMode)) {
    if (textMode === "phonetic") notice.value = "还没有音标，先补充音标后再生成。";
    return;
  }
  generatingKey.value = `${textMode}:${voiceGender}`;
  notice.value = "";
  try {
    const result = await props.generateAiAudio(activeTarget.value.key, voiceGender, textMode);
    applyMediaSources(result);
    const voiceLabel = voiceGender === "male" ? "男声" : "女声";
    setPendingAudio({
      type: "url",
      url: result.audio_url,
      label: `${aiButtonLabel(textMode)} · ${voiceLabel}`,
      sourceMeta: resultSourceMeta(result, activeTarget.value.key, result?.source || "ai-tts", result.audio_url),
    });
    const played = await playPendingAudio();
    notice.value = played
      ? "AI 音频已生成并自动播放，确认后保存。"
      : "AI 音频已生成，浏览器未自动播放时可点上方播放器试听，确认后保存。";
  } catch (error) {
    notice.value = error.message || "AI 朗读生成失败";
  } finally {
    generatingKey.value = "";
  }
}

async function generateFieldAudio() {
  if (!canGenerateFieldAudio.value) {
    notice.value = fieldText.value ? "当前音频处理功能未加载，请刷新页面后重试。" : "当前字段还没有文本，先补全内容后再生成音频。";
    return;
  }
  const key = activeTarget.value.type;
  generatingKey.value = key;
  notice.value = "";
  try {
    const result = key === "definition" ? await props.generateDefinitionAudio({ source: "auto" }) : await props.generateExampleAudio({ source: "auto" });
    applyMediaSources(result);
    const audioUrl = result?.audio_url || (key === "definition" ? word.value.english_definition_audio_url : word.value.english_example_audio_url);
    if (audioUrl) {
      setPendingAudio({
        type: "field",
        url: audioUrl,
        label: `${activeTarget.value.label} · 已保存到服务器`,
        sourceMeta: resultSourceMeta(result, key, result?.source || "resource", audioUrl),
      });
      const played = await playPendingAudio();
      notice.value = played
        ? `${activeTarget.value.label}音频已更新并自动播放。`
        : `${activeTarget.value.label}音频已更新，点上方播放器可试听。`;
    } else {
      notice.value = `${activeTarget.value.label}音频处理完成，但暂时没有可播放文件。`;
    }
  } catch (error) {
    notice.value = error.message || `${activeTarget.value.label}音频处理失败`;
  } finally {
    generatingKey.value = "";
  }
}

async function syncFieldFromSpb() {
  if (!canSyncFieldFromSpb.value) {
    notice.value = fieldText.value ? "当前小程序同步功能未加载，请刷新页面后重试。" : "当前字段还没有文本，先补全文本后再同步。";
    return;
  }
  const key = activeTarget.value.type;
  generatingKey.value = `${key}:spb`;
  notice.value = "";
  try {
    const result = key === "definition" ? await props.generateDefinitionAudio({ source: "spb" }) : await props.generateExampleAudio({ source: "spb" });
    applyMediaSources(result);
    const audioUrl = result?.audio_url || (key === "definition" ? word.value.english_definition_audio_url : word.value.english_example_audio_url);
    if (audioUrl) {
      setPendingAudio({
        type: "field",
        url: audioUrl,
        label: `${activeTarget.value.label} · SPB小程序音频`,
        sourceMeta: resultSourceMeta(result, key, "spb-miniprogram", audioUrl),
      });
      const played = await playPendingAudio();
      notice.value = played
        ? `已同步 SPB 小程序${activeTarget.value.label}音频并自动播放。`
        : `已同步 SPB 小程序${activeTarget.value.label}音频，点上方播放器可试听。`;
    } else {
      notice.value = `SPB 小程序暂时没有返回${activeTarget.value.label}音频。`;
    }
  } catch (error) {
    notice.value = error.message || `同步小程序${activeTarget.value.label}音频失败`;
  } finally {
    generatingKey.value = "";
  }
}

watch(() => props.accent.key, (key) => {
  if (activeTargetKey.value === "us" || activeTargetKey.value === "gb") activeTargetKey.value = key;
  resetPendingAudio();
});

onBeforeUnmount(clearPreviewUrl);
</script>

<template>
  <div class="audio-manager-backdrop" role="dialog" aria-modal="true">
    <section class="audio-manager-modal">
      <header class="audio-manager-heading">
        <div>
          <p class="section-kicker">当前：{{ activeTarget.label }}</p>
          <h2>音频管理</h2>
        </div>
        <button class="ghost-button compact-button" type="button" @click="emit('close')">关闭</button>
      </header>

      <div class="audio-manager-body">
        <section class="audio-manager-section audio-manager-target-panel">
          <div class="audio-manager-target-grid" role="group" aria-label="选择音频类型">
            <button
              v-for="target in audioTargets"
              :key="target.key"
              type="button"
              class="audio-manager-target-button"
              :class="{ active: target.key === activeTarget.key }"
              @click="selectTarget(target.key)"
            >
              <span>{{ target.label }}</span>
              <strong>{{ target.status }}</strong>
              <em class="audio-source-chip">{{ displaySource(target.sourceMeta) }}</em>
              <small>{{ target.subtitle }}</small>
            </button>
          </div>
        </section>

        <section class="audio-manager-section audio-manager-preview">
          <div class="audio-manager-section-head">
            <div>
              <h3>当前试听音频</h3>
              <p>{{ currentAudioLabel }}</p>
              <small v-if="currentAudioUrl" class="audio-manager-current-source">{{ currentAudioSourceText }}</small>
            </div>
            <button
              v-if="isWordTarget"
              class="challenge-button"
              type="button"
              :disabled="!canSavePendingAudio || savingSelection"
              @click="saveCurrentAudio"
            >
              {{ savingSelection ? "保存中..." : "保存当前单词音频" }}
            </button>
            <span v-else class="audio-manager-current-pill">
              {{ activeTarget.currentUrl ? "字段音频已保存" : "字段音频待处理" }}
            </span>
          </div>
          <audio v-if="currentAudioUrl" ref="previewAudio" controls :src="currentAudioUrl" />
          <p v-else class="audio-manager-empty">先从下方选择、上传或生成一个音频。</p>
        </section>

        <template v-if="isWordTarget">
          <section class="audio-manager-section">
            <div class="audio-manager-section-head">
              <div>
                <h3>重新获取单词音频</h3>
                <p>从词典源查找，也可以直接读取 SPB 小程序单词音频。</p>
              </div>
              <div class="audio-manager-button-group">
                <button class="secondary-button" type="button" :disabled="loadingOptions || loadingSpbOptions" @click="refreshOptions">
                  {{ loadingOptions ? "获取中..." : "重新获取音源" }}
                </button>
                <button class="secondary-button" type="button" :disabled="loadingOptions || loadingSpbOptions" @click="refreshSpbOptions">
                  {{ loadingSpbOptions ? "获取中..." : "获取小程序音频" }}
                </button>
              </div>
            </div>
            <div v-if="activeOptions.length" class="audio-manager-options">
              <article v-for="option in activeOptions" :key="option.url" class="audio-manager-option">
                <div>
                  <strong>{{ option.label }}</strong>
                  <small class="audio-source-chip">{{ displaySource(optionSourceMeta(option)) }}</small>
                </div>
                <button class="secondary-button" type="button" @click="previewOption(option)">放入试听</button>
              </article>
            </div>
            <p v-else class="audio-manager-empty">还没有候选音频，点击重新获取音源。</p>
          </section>

          <section class="audio-manager-section">
            <div class="audio-manager-ai-row">
              <div>
                <h3>AI朗读单词</h3>
              </div>
              <div class="audio-manager-button-group">
                <button class="secondary-button" type="button" :disabled="!canGenerateAi('word')" @click="generateAiSource('word', 'female')">
                  {{ aiButtonText("word", "female") }}
                </button>
                <button class="secondary-button" type="button" :disabled="!canGenerateAi('word')" @click="generateAiSource('word', 'male')">
                  {{ aiButtonText("word", "male") }}
                </button>
              </div>
            </div>
            <div class="audio-manager-ai-row">
              <div>
                <h3>AI朗读音标</h3>
                <p>{{ phoneticRowHint }}</p>
              </div>
              <div class="audio-manager-button-group">
                <button class="secondary-button" type="button" :disabled="!canGenerateAi('phonetic')" @click="generateAiSource('phonetic', 'female')">
                  {{ aiButtonText("phonetic", "female") }}
                </button>
                <button class="secondary-button" type="button" :disabled="!canGenerateAi('phonetic')" @click="generateAiSource('phonetic', 'male')">
                  {{ aiButtonText("phonetic", "male") }}
                </button>
              </div>
            </div>
          </section>
        </template>

        <section v-else class="audio-manager-section audio-manager-field-panel">
          <div class="audio-manager-section-head">
            <div>
              <h3>{{ activeTarget.label }}音频</h3>
              <p>{{ activeTarget.subtitle }}</p>
            </div>
            <div class="audio-manager-button-group">
              <button class="secondary-button" type="button" :disabled="!canSyncFieldFromSpb" @click="syncFieldFromSpb">
                {{ fieldSpbSyncText }}
              </button>
              <button class="challenge-button" type="button" :disabled="!canGenerateFieldAudio" @click="generateFieldAudio">
                {{ fieldGenerateText }}
              </button>
            </div>
          </div>
          <p v-if="fieldText" class="audio-manager-field-text">{{ fieldText }}</p>
          <p v-else class="audio-manager-empty">这个字段还没有内容，先补全文本后再生成音频。</p>
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

        <section class="audio-manager-section" :class="{ disabled: !canUseUpload }">
          <div class="audio-manager-section-head">
            <div>
              <h3>上传我的音频</h3>
              <p>{{ canUseUpload ? "选择音频文件后先预览，确认后保存为当前单词发音。" : "上传只用于美式/英式单词音频，定义和例句音频请用上方按钮处理。" }}</p>
            </div>
          </div>
          <label class="audio-upload-picker" :class="{ disabled: !canUseUpload }">
            <input type="file" accept="audio/*" :disabled="!canUseUpload" @change="selectUploadFile">
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

<style scoped>
.audio-source-chip,
.audio-manager-current-source {
  align-self: flex-start;
  width: fit-content;
  border-radius: 999px;
  background: rgba(16, 128, 90, 0.1);
  color: #087452;
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
  line-height: 1;
  padding: 5px 9px;
}

.audio-manager-current-source {
  display: inline-flex;
  margin-top: 6px;
}

.audio-manager-target-button .audio-source-chip {
  margin-top: 2px;
}

.audio-manager-target-button:hover .audio-source-chip,
.audio-manager-target-button.active .audio-source-chip {
  background: rgba(255, 255, 255, 0.24);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.28);
  color: #ffffff;
}

.audio-manager-target-button:hover .audio-source-chip {
  background: rgba(255, 255, 255, 0.3);
}

.audio-manager-option {
  align-items: center;
  gap: 12px;
}

.audio-manager-option > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 6px;
}

.audio-manager-option strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
