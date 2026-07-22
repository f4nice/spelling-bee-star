<script setup>
import { computed, reactive, ref, watch } from "vue";
import { routeApiPaths } from "../routeApiPaths.js";
import { fetchJson } from "../utils.js";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
});

const essays = ref([]);
const selectedId = ref(0);
const notice = ref("");
const busyAction = ref("");
const draft = reactive(emptyDraft());
let isApplyingDraft = false;

const titleMaxChars = computed(() => Number(props.data?.limits?.titleMaxChars || 120));
const bodyMaxChars = computed(() => Number(props.data?.limits?.bodyMaxChars || 30000));
const currentWordCount = computed(() => countEssayWords(draft.body));
const hasEssayInput = computed(() => Boolean(draft.title.trim() && draft.body.trim()));
const aiVersionText = computed(() => {
  if (busyAction.value === "optimize") return "AI 正在优化这篇作文，完成后会显示在这里。";
  return draft.optimizedBody || "AI 优化后会显示在这里。";
});
const aiVersionWordCount = computed(() => (busyAction.value === "optimize" ? 0 : draft.optimizedWordCount || countEssayWords(draft.optimizedBody)));
const selectedEssay = computed(() => essays.value.find((item) => Number(item.id) === Number(selectedId.value)) || null);
const hasEssays = computed(() => essays.value.length > 0);

watch(
  () => props.data,
  (value) => {
    essays.value = Array.isArray(value?.essays) ? value.essays : [];
    if (selectedId.value && essays.value.some((item) => Number(item.id) === Number(selectedId.value))) {
      loadDraft(essays.value.find((item) => Number(item.id) === Number(selectedId.value)));
      return;
    }
    loadDraft(essays.value[0] || null);
  },
  { immediate: true },
);

function emptyDraft() {
  return {
    id: 0,
    title: "",
    body: "",
    optimizedBody: "",
    coverUrl: "",
    wordCount: 0,
    optimizedWordCount: 0,
    aiModel: "",
    coverModel: "",
    updatedAt: "",
  };
}

function assignDraft(value) {
  isApplyingDraft = true;
  Object.assign(draft, value);
  isApplyingDraft = false;
}

function loadDraft(essay) {
  if (!essay) {
    selectedId.value = 0;
    assignDraft(emptyDraft());
    return;
  }
  selectedId.value = Number(essay.id);
  assignDraft({
    id: Number(essay.id),
    title: essay.title || "",
    body: essay.body || "",
    optimizedBody: essay.optimizedBody || "",
    coverUrl: essay.coverUrl || "",
    wordCount: Number(essay.wordCount || 0),
    optimizedWordCount: Number(essay.optimizedWordCount || 0),
    aiModel: essay.aiModel || "",
    coverModel: essay.coverModel || "",
    updatedAt: essay.updatedAt || "",
  });
}

function countEssayWords(value) {
  return (String(value || "").match(/[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+(?:\.\d+)?|[\u4e00-\u9fff]/g) || []).length;
}

function selectEssay(essay) {
  notice.value = "";
  loadDraft(essay);
}

function startNewEssay() {
  notice.value = "";
  loadDraft(null);
}

watch(
  () => [draft.title, draft.body],
  ([nextTitle, nextBody], [previousTitle, previousBody]) => {
    if (isApplyingDraft || (nextTitle === previousTitle && nextBody === previousBody)) return;
    if (draft.optimizedBody || draft.optimizedWordCount || draft.aiModel) {
      draft.optimizedBody = "";
      draft.optimizedWordCount = 0;
      draft.aiModel = "";
    }
    if (draft.coverUrl || draft.coverModel) {
      draft.coverUrl = "";
      draft.coverModel = "";
    }
  },
  { flush: "sync" },
);

function requestPayload() {
  return {
    title: draft.title,
    body: draft.body,
  };
}

function requestOptions() {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestPayload()),
  };
}

function applyResponse(payload) {
  essays.value = Array.isArray(payload?.essays) ? payload.essays : essays.value;
  const nextEssay = payload?.essay || essays.value.find((item) => Number(item.id) === Number(selectedId.value)) || essays.value[0] || null;
  loadDraft(nextEssay);
}

async function persistEssay({ silent = false } = {}) {
  if (!hasEssayInput.value) {
    notice.value = "标题和正文都写好后再保存。";
    return null;
  }
  if (busyAction.value) return null;
  busyAction.value = "save";
  notice.value = "";
  try {
    const url = draft.id ? routeApiPaths.essay(draft.id) : routeApiPaths.essays();
    const payload = await fetchJson(url, requestOptions());
    applyResponse(payload);
    if (!silent) notice.value = "已保存。";
    return payload.essay;
  } catch (error) {
    notice.value = error?.message || "保存失败，请稍后再试。";
    return null;
  } finally {
    busyAction.value = "";
  }
}

async function ensureSavedEssay() {
  if (draft.id) return { id: draft.id };
  return persistEssay({ silent: true });
}

async function optimizeEssay() {
  if (!hasEssayInput.value) {
    notice.value = "标题和正文都写好后再优化。";
    return;
  }
  if (busyAction.value) return;
  const essay = await ensureSavedEssay();
  if (!essay?.id) return;
  busyAction.value = "optimize";
  notice.value = "";
  try {
    const payload = await fetchJson(routeApiPaths.essayOptimize(essay.id), requestOptions());
    applyResponse(payload);
    notice.value = "AI 优化稿已生成。";
  } catch (error) {
    notice.value = error?.message || "AI 优化失败，请稍后再试。";
  } finally {
    busyAction.value = "";
  }
}

async function generateCover() {
  if (!hasEssayInput.value) {
    notice.value = "标题和正文都写好后再生成封面。";
    return;
  }
  if (busyAction.value) return;
  const essay = await ensureSavedEssay();
  if (!essay?.id) return;
  busyAction.value = "cover";
  notice.value = "";
  try {
    const payload = await fetchJson(routeApiPaths.essayCover(essay.id), requestOptions());
    applyResponse(payload);
    notice.value = "封面已生成。";
  } catch (error) {
    notice.value = error?.message || "封面生成失败，请稍后再试。";
  } finally {
    busyAction.value = "";
  }
}

async function deleteEssay() {
  if (!draft.id || !window.confirm(`删除《${draft.title || "未命名作文"}》？`)) return;
  busyAction.value = "delete";
  notice.value = "";
  try {
    const payload = await fetchJson(routeApiPaths.essayDelete(draft.id), { method: "POST" });
    applyResponse(payload);
    notice.value = "已删除。";
  } catch (error) {
    notice.value = error?.message || "删除失败，请稍后再试。";
  } finally {
    busyAction.value = "";
  }
}
</script>

<template>
  <section class="essays-page">
    <header class="essays-page-head">
      <div>
        <span class="eyebrow">ESSAYS</span>
        <h1>我的作文集</h1>
      </div>
      <button type="button" class="secondary-button" @click="startNewEssay">新建作文</button>
    </header>

    <div class="essays-layout">
      <aside class="panel essays-list-panel">
        <div class="essays-list-head">
          <strong>作文</strong>
          <span>{{ essays.length }} 篇</span>
        </div>
        <div v-if="hasEssays" class="essays-list">
          <button
            v-for="essay in essays"
            :key="essay.id"
            type="button"
            class="essay-list-item"
            :class="{ active: selectedEssay && selectedEssay.id === essay.id }"
            @click="selectEssay(essay)"
          >
            <img v-if="essay.coverUrl" :src="essay.coverUrl" :alt="essay.title">
            <span v-else>{{ (essay.title || "作").slice(0, 1).toUpperCase() }}</span>
            <strong>{{ essay.title || "未命名作文" }}</strong>
            <small>{{ essay.wordCount || 0 }} 字</small>
          </button>
        </div>
        <p v-else class="notice">还没有作文。</p>
      </aside>

      <article class="panel essays-editor-panel">
        <div class="essay-editor-head">
          <label class="essay-title-field">
            <span>标题</span>
            <input v-model="draft.title" type="text" :maxlength="titleMaxChars" placeholder="A Day I Will Remember">
          </label>
          <div class="essay-count-pill">
            <span>正文</span>
            <strong>{{ currentWordCount }}</strong>
            <span>字</span>
          </div>
        </div>

        <textarea
          v-model="draft.body"
          class="essay-body-input"
          :maxlength="bodyMaxChars"
          placeholder="在这里输入作文正文..."
        ></textarea>

        <div class="essay-actions">
          <button type="button" class="secondary-button" :disabled="!hasEssayInput || Boolean(busyAction)" @click="persistEssay()">
            {{ busyAction === "save" ? "保存中..." : "保存" }}
          </button>
          <button type="button" class="challenge-button" :disabled="!hasEssayInput || Boolean(busyAction)" @click="optimizeEssay">
            {{ busyAction === "optimize" ? "优化中..." : "AI 优化" }}
          </button>
          <button type="button" class="secondary-button" :disabled="!hasEssayInput || Boolean(busyAction)" @click="generateCover">
            {{ busyAction === "cover" ? "生成中..." : "生成封面" }}
          </button>
          <button v-if="draft.id" type="button" class="secondary-button danger-button" :disabled="Boolean(busyAction)" @click="deleteEssay">
            删除
          </button>
        </div>

        <p v-if="notice" class="notice essay-notice">{{ notice }}</p>

        <div class="essay-workspace">
          <section class="essay-cover-panel">
            <img v-if="draft.coverUrl" :src="draft.coverUrl" :alt="draft.title">
            <div v-else class="essay-cover-fallback">
              <span>作文封面</span>
              <strong>{{ (draft.title || "E").slice(0, 1).toUpperCase() }}</strong>
            </div>
          </section>

          <section class="essay-comparison">
            <article class="essay-text-panel">
              <div class="essay-section-title">
                <span class="eyebrow">MY DRAFT</span>
                <strong>{{ currentWordCount }} 字</strong>
              </div>
              <p>{{ draft.body || "正文会显示在这里。" }}</p>
            </article>
            <article class="essay-text-panel">
              <div class="essay-section-title">
                <span class="eyebrow">AI VERSION</span>
                <strong>{{ aiVersionWordCount }} 字</strong>
              </div>
              <p>{{ aiVersionText }}</p>
            </article>
          </section>
        </div>
      </article>
    </div>
  </section>
</template>
