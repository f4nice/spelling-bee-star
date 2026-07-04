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
  openImportModal: {
    type: Function,
    required: true,
  },
  groups: {
    type: Array,
    default: () => [],
  },
  moveListToGroup: {
    type: Function,
    required: true,
  },
});

const input = ref(null);
const isEditing = ref(false);
const originalName = ref("");
const isMovingGroup = ref(false);
const groupMoveNotice = ref("");

async function startEditing() {
  originalName.value = props.wordList.name || "";
  isEditing.value = true;
  await nextTick();
  input.value?.focus();
  input.value?.select();
}

async function saveTitle() {
  if (!isEditing.value) return;
  const nextName = (props.wordList.name || "").trim();
  if (!nextName) {
    props.wordList.name = originalName.value;
    isEditing.value = false;
    return;
  }
  props.wordList.name = nextName;
  await props.renameList();
  isEditing.value = false;
}

function cancelEditing() {
  props.wordList.name = originalName.value;
  isEditing.value = false;
}

async function changeGroup(event) {
  const nextGroupId = event.target.value;
  if (String(props.wordList.group_id || "") === String(nextGroupId || "")) return;
  isMovingGroup.value = true;
  groupMoveNotice.value = "";
  try {
    await props.moveListToGroup(nextGroupId || null);
    groupMoveNotice.value = "已更新单词组";
    window.setTimeout(() => {
      groupMoveNotice.value = "";
    }, 1800);
  } catch (error) {
    groupMoveNotice.value = error.message || "单词组更新失败";
    event.target.value = String(props.wordList.group_id || "");
  } finally {
    isMovingGroup.value = false;
  }
}
</script>

<template>
  <div :class="['list-title-edit', { 'is-editing': isEditing }]">
    <div class="list-title-line">
      <h1 v-if="!isEditing" title="点击修改名称" @click="startEditing" @dblclick="startEditing">{{ wordList.name }}</h1>
      <input
        v-else
        ref="input"
        v-model="wordList.name"
        class="list-title-input"
        @blur="saveTitle"
        @keydown.enter.prevent="saveTitle"
        @keydown.esc.prevent="cancelEditing"
      >
      <button
        v-if="!isEditing"
        class="secondary-button compact-button list-title-edit-button"
        type="button"
        @click="startEditing"
      >
        修改名称
      </button>
      <template v-else>
        <button class="primary-action-button compact-button list-title-save-button" type="button" @mousedown.prevent @click="saveTitle">保存</button>
        <button class="secondary-button compact-button list-title-cancel-button" type="button" @mousedown.prevent @click="cancelEditing">取消</button>
      </template>
    </div>
    <div class="word-list-meta">
      <p>{{ wordCount }} 个单词</p>
      <button class="ghost-button compact-button" type="button" @click="openImportModal">继续导入</button>
      <label class="word-list-group-picker">
        <span>单词组</span>
        <select :value="wordList.group_id || ''" :disabled="isMovingGroup" @change="changeGroup">
          <option value="">未归组</option>
          <option v-for="group in groups" :key="group.id" :value="group.id">{{ group.name }}</option>
        </select>
      </label>
      <span v-if="groupMoveNotice" class="word-list-group-notice">{{ groupMoveNotice }}</span>
    </div>
  </div>
</template>
