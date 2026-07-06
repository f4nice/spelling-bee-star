<script setup>
import { computed, nextTick, ref } from "vue";

const props = defineProps({
  field: {
    type: String,
    required: true,
  },
  word: {
    type: Object,
    required: true,
  },
  wordEdit: {
    type: Object,
    required: true,
  },
  canEdit: {
    type: Boolean,
    default: false,
  },
  saveWordField: {
    type: Function,
    required: true,
  },
  playAudio: {
    type: Function,
    required: true,
  },
  generateDefinitionAudio: {
    type: Function,
    required: true,
  },
});

const input = ref(null);
const isEditing = ref(false);
const audioPending = ref(false);
const definitionAudioId = computed(() => `definition-audio-${props.word.id || "current"}`);
const exampleAudioId = computed(() => `example-audio-${props.word.id || "current"}`);
const isEnglishDefinition = computed(() => props.field === "english_definition");
const isEnglishExample = computed(() => props.field === "english_example");
const definitionAudioSrc = computed(() => props.word.english_definition_audio_url || "");
const exampleAudioSrc = computed(() => props.word.english_example_audio_url || "");

function isLocalAudioUrl(url) {
  return String(url || "").startsWith("/media/audio/");
}

const canPlayDefinition = computed(() => {
  return Boolean(
    isEnglishDefinition.value &&
      (props.word.english_definition || "").trim() &&
      (isLocalAudioUrl(definitionAudioSrc.value) || props.canEdit),
  );
});

const canPlayExample = computed(() => {
  return Boolean(
    isEnglishExample.value &&
      (props.word.english_example || "").trim() &&
      isLocalAudioUrl(exampleAudioSrc.value),
  );
});

const canPlayFieldAudio = computed(() => canPlayDefinition.value || canPlayExample.value);

async function startEditing() {
  if (!props.canEdit) return;
  isEditing.value = true;
  await nextTick();
  input.value?.focus();
}

async function finishEditing() {
  if (!isEditing.value) return;
  await props.saveWordField(props.field);
  isEditing.value = false;
}

async function playFieldAudio() {
  if (canPlayExample.value) {
    props.playAudio(exampleAudioId.value, "", "en-GB");
    return;
  }
  if (!canPlayDefinition.value || audioPending.value) return;
  if (!isLocalAudioUrl(definitionAudioSrc.value)) {
    audioPending.value = true;
    try {
      const result = await props.generateDefinitionAudio();
      if (result?.audio_url) {
        props.word.english_definition_audio_url = result.audio_url;
      }
    } catch (error) {
      alert(error?.message || "英文定义音频生成失败");
      return;
    } finally {
      audioPending.value = false;
    }
  }
  if (isLocalAudioUrl(definitionAudioSrc.value)) {
    await nextTick();
    props.playAudio(definitionAudioId.value, "", "en-GB");
  }
}
</script>

<template>
  <div :class="['inline-edit definition-inline-edit', { 'is-editing': isEditing }]">
    <div class="definition-display-row">
      <span
        class="inline-edit-text definition-display-text"
        :title="canEdit ? '双击编辑' : ''"
        @dblclick="startEditing"
      >
        {{ word[field] || "暂无" }}
      </span>
      <button
        v-if="canPlayFieldAudio"
        type="button"
        class="definition-audio-button"
        :disabled="audioPending"
        :aria-label="isEnglishDefinition ? '播放英文定义' : '播放英文例句'"
        :title="isEnglishDefinition ? '播放英文定义' : '播放英文例句'"
        @click.stop.prevent="playFieldAudio"
      >
        {{ audioPending ? "..." : "▶" }}
      </button>
      <audio
        v-if="isEnglishDefinition && isLocalAudioUrl(definitionAudioSrc)"
        :id="definitionAudioId"
        :src="definitionAudioSrc"
        preload="none"
      ></audio>
      <audio
        v-if="canPlayExample"
        :id="exampleAudioId"
        :src="exampleAudioSrc"
        preload="none"
      ></audio>
    </div>
    <textarea
      v-if="canEdit"
      ref="input"
      v-model="wordEdit[field]"
      @blur="finishEditing"
    ></textarea>
  </div>
</template>
