<script setup>
import { nextTick, ref } from "vue";

const props = defineProps({
  wordList: {
    type: Object,
    required: true,
  },
  wordCount: {
    type: Number,
    required: true,
  },
  renameList: {
    type: Function,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});

const input = ref(null);
const isEditing = ref(false);

async function startEditing() {
  isEditing.value = true;
  await nextTick();
  input.value?.focus();
  input.value?.select();
}

async function saveTitle() {
  if (!isEditing.value) return;
  await props.renameList();
  isEditing.value = false;
}
</script>

<template>
  <div :class="['list-title-edit', { 'is-editing': isEditing }]">
    <h1 title="双击修改" @dblclick="startEditing">{{ wordList.name }}</h1>
    <input
      ref="input"
      v-model="wordList.name"
      class="list-title-input"
      @blur="saveTitle"
      @keyup.enter="saveTitle"
    >
    <div class="word-list-meta">
      <p>{{ wordCount }} 个单词</p>
      <button class="ghost-button compact-button" type="button" @click="go('/upload')">继续导入</button>
    </div>
  </div>
</template>
