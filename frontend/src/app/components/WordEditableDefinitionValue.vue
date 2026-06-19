<script setup>
import { nextTick, ref } from "vue";

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
});

const input = ref(null);
const isEditing = ref(false);

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
</script>

<template>
  <div :class="['inline-edit definition-inline-edit', { 'is-editing': isEditing }]">
    <span
      class="inline-edit-text definition-display-text"
      :title="canEdit ? '双击编辑' : ''"
      @dblclick="startEditing"
    >
      {{ word[field] || "暂无" }}
    </span>
    <textarea
      v-if="canEdit"
      ref="input"
      v-model="wordEdit[field]"
      @blur="finishEditing"
    ></textarea>
  </div>
</template>
