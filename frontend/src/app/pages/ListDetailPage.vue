<script setup>
import { ref } from "vue";

import ListDetailHeader from "../components/ListDetailHeader.vue";
import ListDetailWordGrid from "../components/ListDetailWordGrid.vue";
import ListImportToolCard from "../components/ListImportToolCard.vue";
import ListsCreateModal from "../components/ListsCreateModal.vue";

const props = defineProps([
  "data",
  "uploadOptions",
  "uploadForm",
  "deleteListState",
  "aiImageJob",
  "submitUpload",
  "renameList",
  "deleteList",
  "moveListToGroup",
  "createWordInList",
  "generateListAiImages",
  "wordDetailUrl",
  "imageForWord",
  "fallbackLetter",
  "go",
]);

const isImportModalOpen = ref(false);
const isCreateWordModalOpen = ref(false);
const isCreatingWord = ref(false);
const createWordNotice = ref("");
const createdWordResult = ref(null);
const newWord = ref(createEmptyWordForm());

function createEmptyWordForm() {
  return {
    word: "",
    phonetic: "",
    part_of_speech: "",
    english_definition: "",
    chinese_definition: "",
    english_example: "",
    note: "",
  };
}

function openCreateWordModal() {
  newWord.value = createEmptyWordForm();
  createdWordResult.value = null;
  createWordNotice.value = "";
  isCreateWordModalOpen.value = true;
}

function closeCreateWordModal() {
  if (isCreatingWord.value) return;
  isCreateWordModalOpen.value = false;
  createdWordResult.value = null;
  createWordNotice.value = "";
}

async function submitNewWord() {
  if (isCreatingWord.value) return;
  if (!newWord.value.word.trim()) {
    createWordNotice.value = "请输入英文单词。";
    return;
  }
  isCreatingWord.value = true;
  createWordNotice.value = "";
  try {
    const result = await props.createWordInList(newWord.value);
    createdWordResult.value = result;
    createWordNotice.value = `已添加 ${result.word?.word || newWord.value.word}`;
    newWord.value = createEmptyWordForm();
  } catch (error) {
    createWordNotice.value = error.message || "单词保存失败，请稍后再试。";
  } finally {
    isCreatingWord.value = false;
  }
}

function openCreatedWord() {
  if (!createdWordResult.value?.detail_url) return;
  props.go(createdWordResult.value.detail_url);
}

function openImportModal() {
  const lists = props.uploadOptions.word_lists || [];
  if (!lists.some((item) => Number(item.id) === Number(props.data.word_list.id))) {
    props.uploadOptions.word_lists = [props.data.word_list, ...lists];
  }
  props.uploadForm.word_list_id = props.data.word_list.id;
  props.uploadForm.word_list_name = "";
  props.uploadForm.file = null;
  isImportModalOpen.value = true;
}
</script>

<template>
  <ListDetailHeader
    :data="data"
    :delete-list-state="deleteListState"
    :rename-list="renameList"
    :delete-list="deleteList"
    :move-list-to-group="moveListToGroup"
    :open-create-word-modal="openCreateWordModal"
    :open-import-modal="openImportModal"
  />
  <ListsCreateModal
    v-if="isCreateWordModalOpen"
    kicker="Word"
    title="新建单词"
    :description="`添加到「${data.word_list.name}」`"
    @close="closeCreateWordModal"
  >
    <form class="manual-word-form" @submit.prevent="submitNewWord">
      <label class="manual-word-field manual-word-field-wide">
        <span>英文单词</span>
        <input
          v-model.trim="newWord.word"
          type="text"
          autocomplete="off"
          placeholder="例如：vacation"
          required
          autofocus
          :disabled="isCreatingWord"
        >
      </label>
      <label class="manual-word-field">
        <span>音标</span>
        <input v-model.trim="newWord.phonetic" type="text" placeholder="/veɪˈkeɪʃn/" :disabled="isCreatingWord">
      </label>
      <label class="manual-word-field">
        <span>词性</span>
        <input v-model.trim="newWord.part_of_speech" type="text" placeholder="noun" :disabled="isCreatingWord">
      </label>
      <label class="manual-word-field manual-word-field-wide">
        <span>英文释义</span>
        <textarea v-model.trim="newWord.english_definition" rows="3" placeholder="A period of time spent away from work or school." :disabled="isCreatingWord"></textarea>
      </label>
      <label class="manual-word-field manual-word-field-wide">
        <span>中文释义</span>
        <textarea v-model.trim="newWord.chinese_definition" rows="2" placeholder="假期；休假" :disabled="isCreatingWord"></textarea>
      </label>
      <label class="manual-word-field manual-word-field-wide">
        <span>英文例句</span>
        <textarea v-model.trim="newWord.english_example" rows="3" placeholder="We had a restful vacation at the beach." :disabled="isCreatingWord"></textarea>
      </label>
      <label class="manual-word-field manual-word-field-wide">
        <span>备注</span>
        <input v-model.trim="newWord.note" type="text" placeholder="可选" :disabled="isCreatingWord">
      </label>
      <p v-if="createWordNotice" class="manual-word-notice">{{ createWordNotice }}</p>
      <div class="manual-word-actions">
        <button class="secondary-button" type="button" :disabled="isCreatingWord" @click="closeCreateWordModal">关闭</button>
        <button
          v-if="createdWordResult?.detail_url"
          class="secondary-button"
          type="button"
          :disabled="isCreatingWord"
          @click="openCreatedWord"
        >
          打开详情
        </button>
        <button class="primary-action-button" type="submit" :disabled="isCreatingWord">
          {{ isCreatingWord ? "保存中..." : "保存单词" }}
        </button>
      </div>
    </form>
  </ListsCreateModal>
  <ListsCreateModal
    v-if="isImportModalOpen"
    kicker="Import"
    title="导入单词"
    description="上传 Excel 到当前单词表，确认预览后合并进来。"
    @close="isImportModalOpen = false"
  >
    <ListImportToolCard
      :upload-options="uploadOptions"
      :upload-form="uploadForm"
      :submit-upload="submitUpload"
    />
  </ListsCreateModal>
  <ListDetailWordGrid
    :data="data"
    :ai-image-job="aiImageJob"
    :generate-list-ai-images="generateListAiImages"
    :word-detail-url="wordDetailUrl"
    :image-for-word="imageForWord"
    :fallback-letter="fallbackLetter"
  />
</template>
