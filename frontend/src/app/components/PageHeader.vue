<script setup>
import { computed, nextTick, ref, watch } from "vue";
import { fetchJson } from "../utils.js";
import { wordApiPaths } from "../wordApiPaths.js";

const props = defineProps({
  routeTitle: {
    type: String,
    required: true,
  },
  route: {
    type: Object,
    default: null,
  },
  data: {
    type: Object,
    default: null,
  },
  go: {
    type: Function,
    default: null,
  },
});

const deletePassword = ref("");
const deleteError = ref("");
const isDeleteOpen = ref(false);
const isDeleting = ref(false);
const passwordInput = ref(null);

const returnList = computed(() => {
  if (props.route?.name !== "wordDetail") return null;
  const nav = props.data?.navigation || {};
  if (!nav.list_id) return null;
  return {
    id: nav.list_id,
    name: nav.word_list_name || "单词表",
  };
});

const canRemoveWordFromList = computed(() => {
  return Boolean(
    props.route?.name === "wordDetail"
      && props.data?.can_edit
      && props.data?.word?.id
      && returnList.value?.id
  );
});

watch(
  () => [props.route?.name, props.route?.params?.id, props.route?.query?.list_id],
  () => {
    isDeleteOpen.value = false;
    deletePassword.value = "";
    deleteError.value = "";
    isDeleting.value = false;
  }
);

function safeInternalReturnPath(value) {
  const text = String(value || "").trim();
  if (!text.startsWith("/") || text.startsWith("//")) return "";
  if (/[\r\n]/.test(text)) return "";
  return text;
}

const returnTarget = computed(() => {
  if (props.route?.name !== "wordDetail") return null;
  const returnTo = safeInternalReturnPath(props.route?.query?.return_to);
  if (returnTo) {
    return {
      href: returnTo,
      label: String(props.route?.query?.return_label || "上一页").trim() || "上一页",
    };
  }
  if (!returnList.value) return null;
  return {
    href: `/lists/${returnList.value.id}`,
    label: returnList.value.name,
  };
});

function goBack(event) {
  if (!returnTarget.value || !props.go) return;
  event.preventDefault();
  props.go(returnTarget.value.href);
}

function openDeleteDialog() {
  deletePassword.value = "";
  deleteError.value = "";
  isDeleteOpen.value = true;
  nextTick(() => passwordInput.value?.focus());
}

function closeDeleteDialog() {
  if (isDeleting.value) return;
  isDeleteOpen.value = false;
  deletePassword.value = "";
  deleteError.value = "";
}

async function removeWordFromList() {
  const listId = returnList.value?.id;
  const wordId = props.data?.word?.id || props.route?.params?.id;
  const password = deletePassword.value.trim();
  if (!listId || !wordId) {
    deleteError.value = "没有找到当前单词表。";
    return;
  }
  if (!password) {
    deleteError.value = "请输入当前账号的登录密码。";
    return;
  }

  const form = new FormData();
  form.append("list_id", String(listId));
  form.append("password", password);
  isDeleting.value = true;
  deleteError.value = "";
  try {
    const result = await fetchJson(wordApiPaths.removeFromList(wordId), { method: "POST", body: form });
    const redirectUrl = result?.redirect_url || `/lists/${listId}`;
    isDeleteOpen.value = false;
    if (props.go) {
      props.go(redirectUrl);
    } else if (typeof window !== "undefined") {
      window.location.assign(redirectUrl);
    }
  } catch (error) {
    deleteError.value = error?.message || "删除失败，请稍后再试。";
  } finally {
    isDeleting.value = false;
  }
}
</script>

<template>
  <section class="panel app-page-heading" :class="{ 'has-return-link': returnTarget }">
    <div class="page-heading-title">
      <p class="section-kicker">SpeakEasy</p>
      <h1>{{ routeTitle }}</h1>
    </div>
    <div v-if="returnTarget || canRemoveWordFromList" class="page-heading-actions">
      <button
        v-if="canRemoveWordFromList"
        class="secondary-button page-heading-delete-button"
        type="button"
        :disabled="isDeleting"
        @click="openDeleteDialog"
      >
        删除单词
      </button>
      <a
        v-if="returnTarget"
        class="secondary-button page-heading-return-button"
        :href="returnTarget.href"
        @click="goBack"
      >
        返回{{ returnTarget.label }}
      </a>
      <form
        v-if="isDeleteOpen"
        class="word-delete-dialog"
        role="dialog"
        aria-label="从单词表删除单词"
        @submit.prevent="removeWordFromList"
      >
        <strong>从“{{ returnList.name }}”删除 {{ routeTitle }}</strong>
        <p>请输入当前账号的登录密码。</p>
        <input
          ref="passwordInput"
          v-model="deletePassword"
          class="word-delete-password"
          type="password"
          autocomplete="current-password"
          placeholder="登录密码"
          :disabled="isDeleting"
        >
        <p v-if="deleteError" class="word-delete-error">{{ deleteError }}</p>
        <div class="word-delete-actions">
          <button class="secondary-button compact-button" type="button" :disabled="isDeleting" @click="closeDeleteDialog">取消</button>
          <button class="primary-button compact-button" type="submit" :disabled="isDeleting">
            {{ isDeleting ? "删除中..." : "确认删除" }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.app-page-heading {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 96px;
  overflow: visible;
  padding: 20px 22px;
  border-color: rgba(29, 127, 91, 0.14);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(239, 248, 243, 0.94));
}

.app-page-heading::after {
  content: "";
  position: absolute;
  right: 22px;
  bottom: 0;
  left: 22px;
  height: 3px;
  border-radius: 999px 999px 0 0;
  background: linear-gradient(90deg, rgba(29, 127, 91, 0.54), rgba(29, 127, 91, 0));
}

.page-heading-title {
  display: grid;
  gap: 8px;
  flex: 1 1 auto;
  min-width: 0;
}

.page-heading-title .section-kicker {
  width: fit-content;
  margin: 0;
  border-radius: 999px;
  padding: 3px 8px;
  color: var(--accent-dark);
  background: #e9f8f1;
  font-size: 11px;
  line-height: 1.2;
}

.page-heading-title h1 {
  margin: 0;
  color: var(--ink);
  font-size: 34px;
  line-height: 1.08;
}

.page-heading-return-button {
  flex: 0 0 auto;
  border-color: rgba(16, 128, 91, 0.32);
  background: #eaf7f1;
  color: #0b6f4c;
  text-decoration: none;
  white-space: nowrap;
}

.page-heading-return-button:hover,
.page-heading-return-button:focus-visible {
  border-color: #0f7f59;
  background: #0f7f59;
  color: #fff;
}

.page-heading-actions {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex: 0 0 auto;
  margin-left: auto;
}

.page-heading-delete-button {
  border-color: rgba(185, 28, 28, 0.28);
  background: #fff7f7;
  color: #b42318;
  white-space: nowrap;
}

.page-heading-delete-button:hover,
.page-heading-delete-button:focus-visible {
  border-color: #b42318;
  background: #b42318;
  color: #fff;
}

.word-delete-dialog {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  display: grid;
  gap: 10px;
  width: min(360px, calc(100vw - 44px));
  border: 1px solid rgba(185, 28, 28, 0.18);
  border-radius: 8px;
  padding: 14px;
  background: #fff;
  box-shadow: 0 18px 42px rgba(20, 35, 31, 0.18);
  color: var(--ink);
}

.word-delete-dialog strong {
  font-size: 15px;
  line-height: 1.35;
}

.word-delete-dialog p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.45;
}

.word-delete-password {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 12px;
  font: inherit;
}

.word-delete-password:focus {
  outline: 2px solid rgba(16, 128, 91, 0.22);
  border-color: #0f7f59;
}

.word-delete-error {
  color: #b42318 !important;
}

.word-delete-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 720px) {
  .app-page-heading {
    align-items: flex-start;
    min-height: auto;
    padding: 18px;
  }

  .page-heading-title h1 {
    font-size: 30px;
  }

  .page-heading-actions {
    width: 100%;
    flex-wrap: wrap;
    justify-content: flex-start;
    margin-left: 0;
  }

  .word-delete-dialog {
    position: static;
    width: 100%;
  }
}
</style>
