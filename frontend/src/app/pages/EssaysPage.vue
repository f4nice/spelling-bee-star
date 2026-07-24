<script setup>
import { computed, nextTick, reactive, ref, watch } from "vue";
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
const deletePassword = ref("");
const deletePasswordInput = ref(null);
const isDeleteConfirmOpen = ref(false);
const draft = reactive(emptyDraft());
let isApplyingDraft = false;

const titleMaxChars = computed(() => Number(props.data?.limits?.titleMaxChars || 120));
const bodyMaxChars = computed(() => Number(props.data?.limits?.bodyMaxChars || 30000));
const currentWordCount = computed(() => countEssayWords(draft.body));
const hasEssayInput = computed(() => Boolean(draft.body.trim()));
const aiVersionText = computed(() => {
  if (busyAction.value === "optimize") return "AI 正在优化这篇作文，完成后会显示在这里。";
  return draft.optimizedBody || "AI 优化后会显示在这里。";
});
const aiVersionWordCount = computed(() => (busyAction.value === "optimize" ? 0 : draft.optimizedWordCount || countEssayWords(draft.optimizedBody)));
const selectedEssay = computed(() => essays.value.find((item) => Number(item.id) === Number(selectedId.value)) || null);
const hasEssays = computed(() => essays.value.length > 0);
const scoreLabels = {
  content: "内容表达",
  length: "篇幅发展",
  vocabulary: "词汇难度",
  grammar: "语法准确",
  structure: "结构连贯",
};
const scoreBreakdownRows = computed(() =>
  Object.entries(scoreLabels).map(([key, label]) => ({
    key,
    label,
    value: Math.min(Math.max(Number(draft.writingScoreBreakdown?.[key] || 0), 0), 100),
  })),
);
const writingPoints = computed(() => scoreBreakdownRows.value.reduce((total, row) => total + row.value, 0));
const writingAdviceRows = computed(() =>
  (Array.isArray(draft.writingAdvice) ? draft.writingAdvice : [])
    .map((item, index) => normalizeWritingAdvice(item, index))
    .filter(Boolean),
);

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
    writingScore: 0,
    writingScoreBreakdown: {},
    writingAdvice: [],
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
    writingScore: Number(essay.writingScore || 0),
    writingScoreBreakdown: essay.writingScoreBreakdown || {},
    writingAdvice: Array.isArray(essay.writingAdvice) ? essay.writingAdvice : [],
    aiModel: essay.aiModel || "",
    coverModel: essay.coverModel || "",
    updatedAt: essay.updatedAt || "",
  });
}

function countEssayWords(value) {
  return (String(value || "").match(/[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+(?:\.\d+)?|[\u4e00-\u9fff]/g) || []).length;
}

function normalizeWritingAdvice(item, index) {
  if (typeof item === "string") {
    const guidance = item.trim();
    return guidance
      ? {
          kind: "老师建议",
          title: `具体建议 ${index + 1}`,
          observation: "",
          guidance,
          original: "",
          example: "",
          wordChoices: [],
        }
      : null;
  }
  if (!item || typeof item !== "object") return null;
  return {
    kind: String(item.kind || "老师建议"),
    title: String(item.title || `具体建议 ${index + 1}`),
    observation: String(item.observation || ""),
    guidance: String(item.guidance || ""),
    original: String(item.original || ""),
    example: String(item.example || ""),
    wordChoices: (Array.isArray(item.wordChoices) ? item.wordChoices : [])
      .filter((choice) => choice && choice.original && choice.better)
      .slice(0, 3),
  };
}

function scoreAchievement(value) {
  if (value >= 90) return "闪耀表现";
  if (value >= 80) return "做得很棒";
  if (value >= 70) return "稳步提升";
  if (value >= 60) return "继续加油";
  return "勇敢起步";
}

function formatEssayCreatedAt(value) {
  if (!value) return "创建时间未知";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "创建时间未知";
  const now = new Date();
  const sameYear = date.getFullYear() === now.getFullYear();
  const formatter = new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    ...(sameYear ? {} : { year: "numeric" }),
  });
  return `创建 ${formatter.format(date)}`;
}

function selectEssay(essay) {
  notice.value = "";
  resetDeleteConfirm();
  loadDraft(essay);
}

function startNewEssay() {
  notice.value = "";
  resetDeleteConfirm();
  loadDraft(null);
}

watch(
  () => [draft.title, draft.body],
  ([nextTitle, nextBody], [previousTitle, previousBody]) => {
    if (isApplyingDraft || (nextTitle === previousTitle && nextBody === previousBody)) return;
    if (draft.optimizedBody || draft.optimizedWordCount || draft.writingScore || draft.aiModel) {
      draft.optimizedBody = "";
      draft.optimizedWordCount = 0;
      draft.writingScore = 0;
      draft.writingScoreBreakdown = {};
      draft.writingAdvice = [];
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
    notice.value = "正文写好后再保存。";
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
    notice.value = "正文写好后再优化。";
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
    notice.value = `AI 优化稿与写作评估已生成，综合得分 ${payload?.essay?.writingScore || 0} 分。`;
  } catch (error) {
    notice.value = error?.message || "AI 优化失败，请稍后再试。";
  } finally {
    busyAction.value = "";
  }
}

async function generateCover() {
  if (!hasEssayInput.value) {
    notice.value = "正文写好后再生成封面。";
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

function resetDeleteConfirm() {
  isDeleteConfirmOpen.value = false;
  deletePassword.value = "";
}

async function openDeleteConfirm() {
  if (!draft.id || busyAction.value) return;
  notice.value = "";
  isDeleteConfirmOpen.value = true;
  await nextTick();
  deletePasswordInput.value?.focus();
}

function cancelDeleteConfirm() {
  if (busyAction.value === "delete") return;
  resetDeleteConfirm();
}

async function deleteEssay() {
  if (!draft.id || busyAction.value) return;
  const password = deletePassword.value.trim();
  if (!password) {
    notice.value = "请输入当前登录密码。";
    return;
  }
  busyAction.value = "delete";
  notice.value = "";
  try {
    const payload = await fetchJson(routeApiPaths.essayDelete(draft.id), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    resetDeleteConfirm();
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
            <small class="essay-list-word-count">{{ essay.wordCount || 0 }} 字</small>
            <small class="essay-list-created-at">{{ formatEssayCreatedAt(essay.createdAt) }}</small>
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

        <div class="essay-actions essay-primary-actions">
          <button type="button" class="challenge-button" :disabled="!hasEssayInput || Boolean(busyAction)" @click="optimizeEssay">
            {{ busyAction === "optimize" ? "优化中..." : "AI 优化" }}
          </button>
        </div>

        <p v-if="notice" class="notice essay-notice">{{ notice }}</p>

        <div class="essay-workspace">
          <section class="essay-cover-column">
            <div class="essay-cover-panel">
              <div v-if="draft.writingScore > 0" class="essay-cover-score-badge" :aria-label="`作文综合得分 ${draft.writingScore} 分`">
                <strong>{{ draft.writingScore }}</strong>
                <span>综合分</span>
              </div>
              <img v-if="draft.coverUrl" :src="draft.coverUrl" :alt="draft.title">
              <div v-else class="essay-cover-fallback">
                <span>作文封面</span>
                <strong>{{ (draft.title || "E").slice(0, 1).toUpperCase() }}</strong>
              </div>
            </div>
            <button type="button" class="secondary-button essay-cover-button" :disabled="!hasEssayInput || Boolean(busyAction)" @click="generateCover">
              {{ busyAction === "cover" ? "生成中..." : "生成封面" }}
            </button>
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

        <section v-if="draft.writingScore > 0" class="essay-writing-feedback" aria-labelledby="essay-writing-feedback-title">
          <header>
            <div>
              <span class="eyebrow">WRITING REVIEW</span>
              <h2 id="essay-writing-feedback-title">写作评估与建议</h2>
            </div>
            <div class="essay-score-total">
              <strong>{{ writingPoints }} / 500</strong>
              <small>综合 {{ draft.writingScore }} / 100</small>
            </div>
          </header>
          <div class="essay-score-breakdown" aria-label="作文评分明细">
            <div v-for="row in scoreBreakdownRows" :key="row.key">
              <span>{{ row.label }} · {{ scoreAchievement(row.value) }}</span>
              <i><b :style="{ width: `${row.value}%` }"></b></i>
              <strong>{{ row.value }} / 100</strong>
            </div>
          </div>
          <div class="essay-energy-reward">
            <span>本篇作文五项积分</span>
            <strong>+{{ writingPoints }} 能量</strong>
            <small>已计入猫咪世界，可用于购买道具和场景。</small>
          </div>
          <div class="essay-writing-advice">
            <h3>英语老师的具体建议</h3>
            <div class="essay-advice-list">
              <article v-for="(advice, index) in writingAdviceRows" :key="`${index}-${advice.title}`" class="essay-advice-item">
                <header>
                  <span>{{ advice.kind }}</span>
                  <h4>{{ advice.title }}</h4>
                </header>
                <p v-if="advice.observation" class="essay-advice-copy">
                  <strong>老师观察</strong>
                  {{ advice.observation }}
                </p>
                <p v-if="advice.guidance" class="essay-advice-copy">
                  <strong>怎么加强</strong>
                  {{ advice.guidance }}
                </p>
                <div v-if="advice.original || advice.example" class="essay-advice-examples">
                  <div v-if="advice.original">
                    <span>原句</span>
                    <p>{{ advice.original }}</p>
                  </div>
                  <div v-if="advice.example">
                    <span>参考改写</span>
                    <p>{{ advice.example }}</p>
                  </div>
                </div>
                <div v-if="advice.wordChoices.length" class="essay-word-choice-list">
                  <strong>词汇升级</strong>
                  <div v-for="choice in advice.wordChoices" :key="`${choice.original}-${choice.better}`">
                    <p>
                      <b>{{ choice.original }}</b>
                      <span aria-hidden="true">→</span>
                      <b>{{ choice.better }}</b>
                    </p>
                    <small v-if="choice.reason">{{ choice.reason }}</small>
                  </div>
                </div>
              </article>
            </div>
          </div>
        </section>

        <div v-if="isDeleteConfirmOpen" class="essay-delete-confirm" role="dialog" aria-label="删除作文确认">
          <div>
            <strong>删除《{{ draft.title || "未命名作文" }}》</strong>
            <span>请输入当前登录密码后删除。</span>
          </div>
          <input
            ref="deletePasswordInput"
            v-model="deletePassword"
            type="password"
            autocomplete="current-password"
            placeholder="登录密码"
            :disabled="busyAction === 'delete'"
            @keydown.enter.prevent="deleteEssay"
          >
          <div class="essay-delete-confirm-actions">
            <button type="button" class="secondary-button" :disabled="busyAction === 'delete'" @click="cancelDeleteConfirm">
              取消
            </button>
            <button type="button" class="secondary-button danger-button" :disabled="busyAction === 'delete'" @click="deleteEssay">
              {{ busyAction === "delete" ? "删除中..." : "确认删除" }}
            </button>
          </div>
        </div>

        <div class="essay-bottom-actions">
          <button v-if="draft.id" type="button" class="secondary-button danger-button" :disabled="Boolean(busyAction)" @click="openDeleteConfirm">
            删除
          </button>
          <button type="button" class="primary-action-button essay-save-button" :disabled="!hasEssayInput || Boolean(busyAction)" @click="persistEssay()">
            {{ busyAction === "save" ? "保存中..." : "保存" }}
          </button>
        </div>
      </article>
    </div>
  </section>
</template>
