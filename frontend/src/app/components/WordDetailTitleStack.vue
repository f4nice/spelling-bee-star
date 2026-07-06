<script setup>
import { computed, nextTick, ref } from "vue";
import { normalizePhonetic } from "../wordEditingActions.js";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  wordEdit: {
    type: Object,
    required: true,
  },
  saveWordField: {
    type: Function,
    required: true,
  },
  playAudio: {
    type: Function,
    required: true,
  },
});

const alternateInput = ref(null);
const phoneticInput = ref(null);
const isEditingAlternate = ref(false);
const isEditingPhonetic = ref(false);
const alternateSpellingsText = computed(() => props.wordEdit.alternate_spellings || props.data.word.alternate_spellings || "");
const hasAlternateSpellings = computed(() => Boolean(String(alternateSpellingsText.value).trim()));
const phoneticText = computed(() => normalizePhonetic(props.wordEdit.phonetic || props.data.word.phonetic || ""));
const hasPhoneticText = computed(() => Boolean(phoneticText.value));
const wordAudioButtons = computed(() => [
  {
    key: "us",
    label: "美式",
    lang: "en-US",
    audioId: "audio-us",
    source: localWordAudioSource("us"),
  },
  {
    key: "gb",
    label: "英式",
    lang: "en-GB",
    audioId: "audio-gb",
    source: localWordAudioSource("gb"),
  },
]);

function isLocalAudioUrl(url) {
  return String(url || "").startsWith("/media/audio/");
}

function localWordAudioSource(accent) {
  const fieldValue = accent === "gb" ? props.data.word.british_audio_url : props.data.word.american_audio_url;
  if (!isLocalAudioUrl(fieldValue)) return "";
  return props.data.audio_sources?.[accent] || fieldValue;
}

function playWordAudio(audio) {
  if (!audio.source) return;
  props.playAudio(audio.audioId, "", audio.lang);
}

async function startAlternateEdit() {
  if (!props.data.can_edit) return;
  props.wordEdit.alternate_spellings = props.data.word.alternate_spellings || props.wordEdit.alternate_spellings || "";
  isEditingAlternate.value = true;
  await nextTick();
  alternateInput.value?.focus();
  alternateInput.value?.select();
}

async function finishAlternateEdit() {
  if (!isEditingAlternate.value) return;
  await props.saveWordField("alternate_spellings");
  isEditingAlternate.value = false;
}

function cancelAlternateEdit() {
  props.wordEdit.alternate_spellings = props.data.word.alternate_spellings || "";
  isEditingAlternate.value = false;
}

async function startPhoneticEdit() {
  if (!props.data.can_edit) return;
  props.wordEdit.phonetic = normalizePhonetic(props.data.word.phonetic || props.wordEdit.phonetic || "");
  isEditingPhonetic.value = true;
  await nextTick();
  phoneticInput.value?.focus();
  phoneticInput.value?.select();
}

async function finishPhoneticEdit() {
  if (!isEditingPhonetic.value) return;
  props.wordEdit.phonetic = normalizePhonetic(props.wordEdit.phonetic);
  await props.saveWordField("phonetic");
  props.wordEdit.phonetic = normalizePhonetic(props.data.word.phonetic);
  isEditingPhonetic.value = false;
}

function cancelPhoneticEdit() {
  props.wordEdit.phonetic = normalizePhonetic(props.data.word.phonetic);
  isEditingPhonetic.value = false;
}
</script>

<template>
  <div class="word-title-stack">
    <div class="word-title-main">
      <h1 :title="data.can_edit ? '双击编辑其他拼法' : null" @dblclick="startAlternateEdit">{{ data.word.word }}</h1>
      <input
        v-if="data.can_edit && isEditingAlternate"
        ref="alternateInput"
        v-model="wordEdit.alternate_spellings"
        class="inline-edit-input title-alternate-edit"
        placeholder="其他拼法"
        aria-label="编辑其他拼法"
        @blur="finishAlternateEdit"
        @keydown.enter.prevent="finishAlternateEdit"
        @keydown.esc.prevent="cancelAlternateEdit"
      >
      <strong v-else-if="hasAlternateSpellings" class="title-alternate-text">{{ alternateSpellingsText }}</strong>
    </div>
    <input
      v-if="data.can_edit && isEditingPhonetic"
      ref="phoneticInput"
      v-model="wordEdit.phonetic"
      class="inline-edit-input phonetic-edit-input"
      aria-label="编辑音标"
      placeholder="输入音标"
      @blur="finishPhoneticEdit"
      @dblclick.stop
      @keydown.enter.prevent="finishPhoneticEdit"
      @keydown.esc.prevent="cancelPhoneticEdit"
    >
    <p
      v-else-if="hasPhoneticText || data.can_edit"
      :class="['phonetic', { 'is-placeholder': !hasPhoneticText }]"
      :title="data.can_edit ? '双击编辑音标' : null"
      @dblclick.stop="startPhoneticEdit"
    >
      {{ hasPhoneticText ? `/${phoneticText}/` : "双击添加音标" }}
    </p>
    <div class="word-audio-quick-controls" aria-label="单词音频">
      <label
        v-for="audio in wordAudioButtons"
        :key="audio.key"
        class="word-audio-quick-item"
      >
        <span>{{ audio.label }}</span>
        <button
          type="button"
          class="word-audio-quick-button"
          :disabled="!audio.source"
          :title="audio.source ? `播放${audio.label}单词` : `${audio.label}单词音频未就绪，请到音频管理处理`"
          @click="playWordAudio(audio)"
        >
          <span aria-hidden="true">▶</span>
        </button>
        <audio
          v-if="audio.source"
          :id="audio.audioId"
          :src="audio.source"
          preload="metadata"
        ></audio>
      </label>
    </div>
  </div>
</template>
