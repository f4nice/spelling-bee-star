<script setup>
import { computed, nextTick, reactive, ref, watch } from "vue";
import { CalendarDays, PenLine } from "lucide-vue-next";
import { essayDailyPromptForDate } from "../essayDailyPrompt.js";
import { sortEssaysNewestFirst } from "../essaySorting.js";
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
const bodyInput = ref(null);
const isDeleteConfirmOpen = ref(false);
const draft = reactive(emptyDraft());
let isApplyingDraft = false;

const titleMaxChars = computed(() => Number(props.data?.limits?.titleMaxChars || 120));
const bodyMaxChars = computed(() => Number(props.data?.limits?.bodyMaxChars || 30000));
const currentWordCount = computed(() => countEssayWords(draft.body));
const hasEssayInput = computed(() => Boolean(draft.body.trim()));
const dailyPrompt = computed(() => essayDailyPromptForDate(new Date()));
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
    essays.value = sortEssaysNewestFirst(value?.essays);
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
    translationBody: "",
    optimizedTranslationBody: "",
    coverUrl: "",
    wordCount: 0,
    optimizedWordCount: 0,
    writingScore: 0,
    writingScoreBreakdown: {},
    writingAdvice: [],
    bestWritingScore: 0,
    bestWritingPoints: 0,
    aiModel: "",
    translationModel: "",
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
    translationBody: essay.translationBody || "",
    optimizedTranslationBody: essay.optimizedTranslationBody || "",
    coverUrl: essay.coverUrl || "",
    wordCount: Number(essay.wordCount || 0),
    optimizedWordCount: Number(essay.optimizedWordCount || 0),
    writingScore: Number(essay.writingScore || 0),
    writingScoreBreakdown: essay.writingScoreBreakdown || {},
    writingAdvice: Array.isArray(essay.writingAdvice) ? essay.writingAdvice : [],
    bestWritingScore: Number(essay.bestWritingScore || 0),
    bestWritingPoints: Number(essay.bestWritingPoints || 0),
    aiModel: essay.aiModel || "",
    translationModel: essay.translationModel || "",
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
          kind: "",
          title: `AI老师建议${index + 1}`,
          observation: "",
          guidance,
          original: "",
          example: "",
          wordChoices: [],
          actionLabel: adviceActionLabel({ guidance }),
        }
      : null;
  }
  if (!item || typeof item !== "object") return null;
  const normalized = {
    kind: String(item.kind || ""),
    title: String(item.title || `AI老师建议${index + 1}`),
    observation: String(item.observation || ""),
    guidance: String(item.guidance || ""),
    original: String(item.original || ""),
    example: String(item.example || ""),
    wordChoices: (Array.isArray(item.wordChoices) ? item.wordChoices : [])
      .filter((choice) => choice && choice.original && choice.better)
      .slice(0, 3),
  };
  return { ...normalized, actionLabel: adviceActionLabel(normalized) };
}

function adviceActionLabel(advice) {
  const text = `${advice?.kind || ""} ${advice?.title || ""} ${advice?.observation || ""} ${advice?.guidance || ""}`;
  if (/委婉|语气|礼貌|直接/.test(text)) return "委婉表达";
  if (/语法|时态|大小写|标点|单复数|冠词/.test(text)) return "语法修正";
  if (/句式|连接词|长句|短句|从句/.test(text)) return "句式优化";
  if (/词汇|用词|名词|动词|形容词|副词|重复/.test(text)) return "词汇升级";
  if (/内容|描写|细节|画面|动作|对话|心理|感官/.test(text)) return "细节扩写";
  if (/结构|段落|开头|结尾|逻辑|衔接|顺序/.test(text)) return "结构调整";
  return "改进方法";
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

async function startDailyPrompt() {
  startNewEssay();
  draft.title = dailyPrompt.value.title;
  notice.value = `今日命题已载入：${dailyPrompt.value.sourceLabel} · ${dailyPrompt.value.typeLabel}`;
  await nextTick();
  bodyInput.value?.focus();
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
    if (draft.translationBody || draft.optimizedTranslationBody || draft.translationModel) {
      draft.translationBody = "";
      draft.optimizedTranslationBody = "";
      draft.translationModel = "";
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
  essays.value = Array.isArray(payload?.essays)
    ? sortEssaysNewestFirst(payload.essays)
    : essays.value;
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
    const currentPoints = Number(payload?.essay?.writingPoints || 0);
    const bestPoints = Number(payload?.essay?.bestWritingPoints || 0);
    const energyGain = Number(payload?.energyGain || 0);
    if (energyGain > 0) {
      notice.value = `本次五项积分 ${currentPoints} 分，超过历史最高，新增 ${energyGain} 能量；当前最高 ${bestPoints} 分。`;
    } else if (payload?.energyGainEligible === false) {
      notice.value = `内容没有修改，本次不重复增加能量；历史最高保持 ${bestPoints} 分。`;
    } else {
      notice.value = `本次五项积分 ${currentPoints} 分，未超过历史最高 ${bestPoints} 分，能量保持不变。`;
    }
  } catch (error) {
    notice.value = error?.message || "AI 优化失败，请稍后再试。";
  } finally {
    busyAction.value = "";
  }
}

async function translateEssay() {
  if (!hasEssayInput.value) {
    notice.value = "正文写好后再翻译。";
    return;
  }
  if (busyAction.value) return;
  const essay = await ensureSavedEssay();
  if (!essay?.id) return;
  busyAction.value = "translate";
  notice.value = "";
  try {
    const payload = await fetchJson(routeApiPaths.essayTranslate(essay.id), requestOptions());
    applyResponse(payload);
    notice.value = draft.optimizedBody
      ? "原稿和 AI 优化稿的中文译文已生成。"
      : "原稿的中文译文已生成。";
  } catch (error) {
    notice.value = error?.message || "一键翻译失败，请稍后再试。";
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
        <section class="essay-daily-prompt" aria-labelledby="essay-daily-prompt-title">
          <header>
            <span><CalendarDays :size="16" aria-hidden="true" />每日命题</span>
            <em>{{ dailyPrompt.sourceLabel }}</em>
          </header>
          <strong id="essay-daily-prompt-title">{{ dailyPrompt.title }}</strong>
          <p>{{ dailyPrompt.prompt }}</p>
          <footer>
            <small>{{ dailyPrompt.typeLabel }} · {{ dailyPrompt.wordRange }}</small>
            <button type="button" class="secondary-button" @click="startDailyPrompt">
              <PenLine :size="16" aria-hidden="true" />
              开始写作
            </button>
          </footer>
        </section>
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
          ref="bodyInput"
          v-model="draft.body"
          class="essay-body-input"
          :maxlength="bodyMaxChars"
          placeholder="在这里输入作文正文..."
        ></textarea>

        <div class="essay-actions essay-primary-actions">
          <button type="button" class="challenge-button" :disabled="!hasEssayInput || Boolean(busyAction)" @click="optimizeEssay">
            {{ busyAction === "optimize" ? "优化中..." : "AI 优化" }}
          </button>
          <button type="button" class="secondary-button" :disabled="!hasEssayInput || Boolean(busyAction)" @click="translateEssay">
            {{ busyAction === "translate" ? "翻译中..." : "一键翻译" }}
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
              <p class="essay-english-copy">{{ draft.body || "正文会显示在这里。" }}</p>
              <section v-if="draft.translationBody" class="essay-translation-block">
                <strong>中文译文</strong>
                <p>{{ draft.translationBody }}</p>
              </section>
            </article>
            <article class="essay-text-panel">
              <div class="essay-section-title">
                <span class="eyebrow">AI VERSION</span>
                <strong>{{ aiVersionWordCount }} 字</strong>
              </div>
              <p class="essay-english-copy">{{ aiVersionText }}</p>
              <section v-if="draft.optimizedTranslationBody" class="essay-translation-block">
                <strong>中文译文</strong>
                <p>{{ draft.optimizedTranslationBody }}</p>
              </section>
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
            <span>本篇作文历史最高</span>
            <strong>{{ draft.bestWritingPoints }} / 500 能量</strong>
            <small v-if="writingPoints >= draft.bestWritingPoints">本次达到历史最高，已计入猫咪世界。</small>
            <small v-else>本次 {{ writingPoints }} 分未超过最高值，已获得能量不会减少。</small>
          </div>
          <div class="essay-writing-advice">
            <h3>英语老师的具体建议</h3>
            <div class="essay-advice-list">
              <article v-for="(advice, index) in writingAdviceRows" :key="`${index}-${advice.title}`" class="essay-advice-item">
                <header>
                  <span v-if="advice.kind">{{ advice.kind }}</span>
                  <h4>{{ advice.title }}</h4>
                </header>
                <p v-if="advice.observation" class="essay-advice-copy">
                  <strong>老师观察</strong>
                  {{ advice.observation }}
                </p>
                <p v-if="advice.guidance" class="essay-advice-copy">
                  <strong>{{ advice.actionLabel }}</strong>
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
