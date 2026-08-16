<script setup>
import { computed, reactive, ref, watch } from "vue";
import {
  BookOpen,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock3,
  RotateCcw,
  Save,
  Sparkles,
} from "lucide-vue-next";
import { countDiaryWords, diaryWordsRemaining, diaryWritingProgress } from "../diaryWriting.js";
import { routeApiPaths } from "../routeApiPaths.js";
import { fetchJson } from "../utils.js";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
});

const payload = ref({});
const selectedDate = ref("");
const busyAction = ref("");
const notice = ref("");
const draft = reactive(emptyDraft());

const rules = computed(() => payload.value?.rules || {});
const today = computed(() => String(payload.value?.today || ""));
const entries = computed(() => (Array.isArray(payload.value?.entries) ? payload.value.entries : []));
const minimumWords = computed(() => Number(rules.value.minimumWords || 100));
const rewardMinutes = computed(() => Number(rules.value.rewardMinutes || 10));
const titleMaxChars = computed(() => Number(rules.value.titleMaxChars || 120));
const bodyMaxChars = computed(() => Number(rules.value.bodyMaxChars || 12000));
const isToday = computed(() => selectedDate.value === today.value);
const wordCount = computed(() => countDiaryWords(draft.body));
const wordsRemaining = computed(() => diaryWordsRemaining(draft.body, minimumWords.value));
const writingProgress = computed(() => `${diaryWritingProgress(draft.body, minimumWords.value) * 100}%`);
const canComplete = computed(() => isToday.value && wordCount.value >= minimumWords.value && !busyAction.value);
const guidance = computed(() => draft.guidance || emptyGuidance());
const hasGuidance = computed(() => Boolean(guidance.value.overall || guidance.value.suggestions?.length));
const hasReward = computed(() => Boolean(draft.rewardedAt));
const todayEntry = computed(() => entries.value.find((entry) => entry.date === today.value) || null);

watch(
  () => props.data,
  (value) => applyPayload(value),
  { immediate: true },
);

function emptyGuidance() {
  return {
    score: 0,
    overall: "",
    strengths: [],
    suggestions: [],
    corrections: [],
    nextFocus: "",
  };
}

function emptyDraft(dateValue = "") {
  return {
    id: 0,
    date: dateValue,
    title: "",
    body: "",
    wordCount: 0,
    guidance: emptyGuidance(),
    aiModel: "",
    completedAt: "",
    rewardedAt: "",
  };
}

function applyPayload(value, preferredDate = "") {
  payload.value = value || {};
  const targetDate = preferredDate || selectedDate.value || String(value?.today || "");
  const entry = (value?.entries || []).find((item) => item.date === targetDate);
  selectedDate.value = targetDate || String(value?.today || "");
  loadDraft(entry || emptyDraft(selectedDate.value));
}

function loadDraft(entry) {
  Object.assign(draft, emptyDraft(entry?.date || selectedDate.value), {
    ...entry,
    guidance: entry?.guidance || emptyGuidance(),
  });
}

function selectEntry(entry) {
  selectedDate.value = entry.date;
  loadDraft(entry);
  notice.value = "";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function returnToToday() {
  selectedDate.value = today.value;
  loadDraft(todayEntry.value || emptyDraft(today.value));
  notice.value = "";
}

function requestOptions() {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: draft.title, body: draft.body }),
  };
}

async function saveDraft() {
  if (!isToday.value || busyAction.value) return;
  busyAction.value = "save";
  notice.value = "";
  try {
    const response = await fetchJson(routeApiPaths.diary(), requestOptions());
    applyPayload(response, response.today);
    notice.value = "今天的日记草稿已保存。";
  } catch (error) {
    notice.value = error?.message || "日记保存失败，请稍后再试。";
  } finally {
    busyAction.value = "";
  }
}

async function completeDiary() {
  if (!canComplete.value) return;
  busyAction.value = "complete";
  notice.value = "";
  try {
    const response = await fetchJson(routeApiPaths.diaryComplete(), requestOptions());
    applyPayload(response, response.today);
    notice.value = response.rewardGranted
      ? `日记完成，猫咪陪伴时间已增加 ${rewardMinutes.value} 分钟。`
      : "AI 指导已更新，今天的 10 分钟奖励已经领取过了。";
  } catch (error) {
    notice.value = error?.message || "AI 日记指导失败，请稍后再试。";
  } finally {
    busyAction.value = "";
  }
}

function formatDate(value) {
  if (!value) return "今天";
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", weekday: "short" }).format(parsed);
}

function entryStatus(entry) {
  if (entry.completedAt) return "已完成";
  return `${Number(entry.wordCount || 0)} 词`;
}
</script>

<template>
  <section class="diary-page">
    <header class="panel diary-hero">
      <div class="diary-hero-title">
        <span class="diary-hero-icon"><BookOpen :size="28" aria-hidden="true" /></span>
        <div>
          <p class="section-kicker">English Diary</p>
          <h1>英文日记本</h1>
        </div>
      </div>
      <div class="diary-rule-strip" aria-label="日记完成规则">
        <span><CalendarDays :size="18" aria-hidden="true" /> 每日一篇</span>
        <span><CheckCircle2 :size="18" aria-hidden="true" /> {{ minimumWords }}+ 词</span>
        <span><Clock3 :size="18" aria-hidden="true" /> 完成 +{{ rewardMinutes }} 分钟</span>
      </div>
    </header>

    <p v-if="notice" class="diary-notice" role="status">{{ notice }}</p>

    <div class="diary-workspace">
      <section class="panel diary-editor-panel" aria-labelledby="diary-editor-title">
        <header class="diary-panel-head">
          <div>
            <p class="section-kicker">{{ isToday ? "Today" : "Archive" }}</p>
            <h2 id="diary-editor-title">{{ formatDate(selectedDate) }}</h2>
          </div>
          <div class="diary-editor-actions">
            <button v-if="!isToday" type="button" class="secondary-button diary-icon-button" @click="returnToToday">
              <RotateCcw :size="17" aria-hidden="true" /> 回到今天
            </button>
            <button v-else type="button" class="secondary-button diary-icon-button" :disabled="Boolean(busyAction)" @click="saveDraft">
              <Save :size="17" aria-hidden="true" /> {{ busyAction === "save" ? "保存中..." : "保存草稿" }}
            </button>
          </div>
        </header>

        <label class="diary-title-field">
          <span>Title</span>
          <input
            v-model="draft.title"
            type="text"
            :maxlength="titleMaxChars"
            :readonly="!isToday"
            placeholder="A small moment from today"
          >
        </label>
        <label class="diary-body-field">
          <span class="sr-only">Diary</span>
          <textarea
            v-model="draft.body"
            :maxlength="bodyMaxChars"
            :readonly="!isToday"
            placeholder="Today I..."
          />
        </label>

        <footer class="diary-editor-footer">
          <div class="diary-progress-block">
            <div class="diary-progress-copy">
              <strong>{{ wordCount }} / {{ minimumWords }} words</strong>
              <span v-if="wordsRemaining">还差 {{ wordsRemaining }} 词</span>
              <span v-else>已达到完成字数</span>
            </div>
            <div class="diary-progress-track" aria-hidden="true">
              <span :style="{ width: writingProgress }" />
            </div>
          </div>
          <button
            v-if="isToday"
            type="button"
            class="primary-action-button diary-complete-button"
            :disabled="!canComplete"
            @click="completeDiary"
          >
            <Sparkles :size="18" aria-hidden="true" />
            {{ busyAction === "complete" ? "AI 阅读中..." : hasReward ? "更新 AI 指导" : "完成并领取 10 分钟" }}
          </button>
        </footer>
      </section>

      <aside class="panel diary-feedback-panel" aria-labelledby="diary-feedback-title">
        <header class="diary-panel-head">
          <div>
            <p class="section-kicker">AI Writing Coach</p>
            <h2 id="diary-feedback-title">写作意见</h2>
          </div>
          <strong v-if="hasGuidance" class="diary-score">{{ guidance.score }}</strong>
        </header>

        <div v-if="hasGuidance" class="diary-feedback-content">
          <p class="diary-overall">{{ guidance.overall }}</p>

          <section v-if="guidance.strengths?.length" class="diary-feedback-group">
            <h3>写得好的地方</h3>
            <ul>
              <li v-for="item in guidance.strengths" :key="item">{{ item }}</li>
            </ul>
          </section>

          <section v-if="guidance.suggestions?.length" class="diary-feedback-group">
            <h3>下一步怎么改</h3>
            <article v-for="item in guidance.suggestions" :key="`${item.title}-${item.guidance}`" class="diary-advice-row">
              <strong>{{ item.title }}</strong>
              <p>{{ item.guidance }}</p>
              <blockquote v-if="item.example">{{ item.example }}</blockquote>
            </article>
          </section>

          <section v-if="guidance.corrections?.length" class="diary-feedback-group">
            <h3>句子修正</h3>
            <div v-for="item in guidance.corrections" :key="`${item.original}-${item.better}`" class="diary-correction-row">
              <del>{{ item.original }}</del>
              <span><ChevronRight :size="15" aria-hidden="true" /> {{ item.better }}</span>
              <small v-if="item.reason">{{ item.reason }}</small>
            </div>
          </section>

          <p v-if="guidance.nextFocus" class="diary-next-focus">
            <Sparkles :size="17" aria-hidden="true" />
            <span><strong>下一篇关注：</strong>{{ guidance.nextFocus }}</span>
          </p>
        </div>
        <div v-else class="diary-feedback-empty">
          <Sparkles :size="32" aria-hidden="true" />
          <strong>{{ draft.completedAt ? "AI 指导正在准备" : "写完后，AI 老师会在这里留下意见" }}</strong>
          <span>会指出亮点、具体修改方法和可参考的英文句子。</span>
        </div>
      </aside>
    </div>

    <section class="panel diary-archive" aria-labelledby="diary-archive-title">
      <header class="diary-panel-head">
        <div>
          <p class="section-kicker">Notebook</p>
          <h2 id="diary-archive-title">日记记录</h2>
        </div>
        <span>{{ entries.length }} 篇</span>
      </header>
      <div v-if="entries.length" class="diary-archive-list">
        <button
          v-for="entry in entries"
          :key="entry.id"
          type="button"
          class="diary-archive-button"
          :class="{ active: entry.date === selectedDate }"
          @click="selectEntry(entry)"
        >
          <CalendarDays :size="19" aria-hidden="true" />
          <span>
            <strong>{{ entry.title }}</strong>
            <small>{{ formatDate(entry.date) }} · {{ entryStatus(entry) }}</small>
          </span>
          <CheckCircle2 v-if="entry.completedAt" :size="18" aria-label="已完成" />
          <ChevronRight v-else :size="18" aria-hidden="true" />
        </button>
      </div>
      <p v-else class="diary-archive-empty">今天会成为这里的第一篇记录。</p>
    </section>
  </section>
</template>

<style scoped>
.diary-page {
  display: grid;
  gap: 18px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.diary-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 22px 24px;
  border-top: 5px solid #1a7d5b;
  background: #fffef9;
}

.diary-hero-title,
.diary-panel-head,
.diary-editor-actions,
.diary-rule-strip,
.diary-icon-button,
.diary-complete-button,
.diary-next-focus {
  display: flex;
  align-items: center;
}

.diary-hero-title {
  gap: 14px;
}

.diary-hero-icon {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border: 2px solid #213147;
  border-radius: 8px;
  background: #ffdc72;
  color: #213147;
  box-shadow: 4px 4px 0 #213147;
}

.diary-hero h1,
.diary-panel-head h2 {
  margin: 0;
  color: #17243a;
  letter-spacing: 0;
}

.diary-hero h1 {
  font-size: 30px;
}

.diary-hero .section-kicker,
.diary-panel-head .section-kicker {
  margin: 0 0 4px;
  color: #147052;
}

.diary-rule-strip {
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.diary-rule-strip span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 38px;
  border: 1px solid #cbd8d1;
  border-radius: 6px;
  padding: 0 11px;
  background: #f5faf7;
  color: #27443a;
  font-size: 13px;
  font-weight: 800;
}

.diary-rule-strip span:nth-child(2) {
  background: #fff6cf;
  color: #5d4a08;
}

.diary-rule-strip span:nth-child(3) {
  background: #e8f4ff;
  color: #15527a;
}

.diary-notice {
  margin: 0;
  border: 1px solid #d5c8dc;
  border-left: 5px solid #a35a9d;
  border-radius: 6px;
  padding: 11px 14px;
  background: #fff7fd;
  color: #743268;
  font-weight: 800;
}

.diary-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(330px, 0.85fr);
  gap: 18px;
  align-items: start;
}

.diary-editor-panel,
.diary-feedback-panel,
.diary-archive {
  padding: 20px;
}

.diary-panel-head {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.diary-panel-head h2 {
  font-size: 23px;
}

.diary-editor-actions {
  gap: 8px;
}

.diary-icon-button,
.diary-complete-button {
  justify-content: center;
  gap: 7px;
}

.diary-title-field,
.diary-body-field {
  display: grid;
  gap: 7px;
}

.diary-title-field span {
  color: #536077;
  font-size: 12px;
  font-weight: 900;
  text-transform: uppercase;
}

.diary-title-field input,
.diary-body-field textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #bfc9c4;
  border-radius: 6px;
  background: #fff;
  color: #17243a;
  font: inherit;
}

.diary-title-field input {
  height: 46px;
  padding: 0 13px;
  font-size: 18px;
  font-weight: 800;
}

.diary-body-field {
  margin-top: 12px;
}

.diary-body-field textarea {
  min-height: 390px;
  resize: vertical;
  padding: 16px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 18px;
  line-height: 1.75;
}

.diary-title-field input:focus,
.diary-body-field textarea:focus {
  outline: 3px solid rgba(26, 125, 91, 0.16);
  border-color: #1a7d5b;
}

.diary-title-field input[readonly],
.diary-body-field textarea[readonly] {
  background: #f7f5ed;
}

.diary-editor-footer {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto;
  gap: 16px;
  align-items: end;
  margin-top: 14px;
}

.diary-progress-block {
  display: grid;
  gap: 7px;
}

.diary-progress-copy {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #536077;
  font-size: 13px;
}

.diary-progress-copy strong {
  color: #17243a;
}

.diary-progress-track {
  height: 9px;
  overflow: hidden;
  border: 1px solid #9cabaa;
  border-radius: 5px;
  background: #e8eeeb;
}

.diary-progress-track span {
  display: block;
  height: 100%;
  background: #1a7d5b;
  transition: width 180ms ease;
}

.diary-complete-button {
  min-height: 44px;
  padding: 0 16px;
  white-space: nowrap;
}

.diary-complete-button,
.diary-complete-button:hover,
.diary-complete-button:focus-visible,
.diary-complete-button:active {
  color: #fff;
}

.diary-complete-button:disabled {
  color: #7b827e;
}

.diary-feedback-panel {
  border-top: 5px solid #5c7fba;
}

.diary-score {
  display: grid;
  width: 50px;
  height: 50px;
  place-items: center;
  border: 2px solid #213147;
  border-radius: 50%;
  background: #f5a9c8;
  color: #213147;
  font-size: 22px;
  box-shadow: 3px 3px 0 #213147;
}

.diary-feedback-content {
  display: grid;
  gap: 18px;
}

.diary-overall {
  margin: 0;
  border-left: 4px solid #5c7fba;
  padding: 10px 0 10px 13px;
  color: #344258;
  line-height: 1.65;
}

.diary-feedback-group {
  display: grid;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid #d9dfdc;
}

.diary-feedback-group h3 {
  margin: 0;
  color: #17243a;
  font-size: 16px;
}

.diary-feedback-group ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 19px;
  color: #405063;
  line-height: 1.55;
}

.diary-advice-row {
  display: grid;
  gap: 5px;
  border-left: 3px solid #e7b643;
  padding: 5px 0 5px 12px;
}

.diary-advice-row p,
.diary-advice-row blockquote {
  margin: 0;
}

.diary-advice-row p {
  color: #4b5869;
  line-height: 1.55;
}

.diary-advice-row blockquote {
  padding: 8px 10px;
  background: #f3f7fb;
  color: #284c6d;
  font-family: Georgia, "Times New Roman", serif;
  line-height: 1.5;
}

.diary-correction-row {
  display: grid;
  gap: 5px;
  border-bottom: 1px solid #e2e6e3;
  padding: 5px 0 10px;
}

.diary-correction-row del {
  color: #9b4d58;
}

.diary-correction-row > span {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  color: #126847;
  font-weight: 800;
}

.diary-correction-row small {
  color: #667085;
  line-height: 1.45;
}

.diary-next-focus {
  align-items: flex-start;
  gap: 8px;
  margin: 0;
  border: 1px solid #e3c767;
  border-radius: 6px;
  padding: 11px;
  background: #fff8d9;
  color: #5c4a11;
  line-height: 1.5;
}

.diary-feedback-empty {
  display: grid;
  min-height: 360px;
  place-content: center;
  justify-items: center;
  gap: 10px;
  padding: 24px;
  color: #647285;
  text-align: center;
}

.diary-feedback-empty strong {
  color: #314056;
}

.diary-feedback-empty span {
  max-width: 320px;
  line-height: 1.55;
}

.diary-archive-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.diary-archive-button {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  min-height: 64px;
  border: 1px solid #bdc8c2;
  border-radius: 6px;
  padding: 9px 11px;
  background: #fff;
  color: #253348;
  text-align: left;
}

.diary-archive-button > span {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.diary-archive-button strong,
.diary-archive-button small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diary-archive-button small {
  color: #687589;
}

.diary-archive-button:hover,
.diary-archive-button:focus-visible {
  border-color: #1a7d5b;
  color: #126847;
}

.diary-archive-button.active,
.diary-archive-button.active:hover,
.diary-archive-button.active:focus-visible {
  border-color: #1a7d5b;
  background: #1a7d5b;
  color: #fff;
}

.diary-archive-button.active small {
  color: #fff;
}

.diary-archive-empty {
  margin: 0;
  color: #687589;
}

@media (max-width: 980px) {
  .diary-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .diary-rule-strip {
    justify-content: flex-start;
  }

  .diary-workspace {
    grid-template-columns: 1fr;
  }

  .diary-archive-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .diary-hero,
  .diary-editor-panel,
  .diary-feedback-panel,
  .diary-archive {
    padding: 16px;
  }

  .diary-hero h1 {
    font-size: 26px;
  }

  .diary-panel-head,
  .diary-editor-footer {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .diary-panel-head {
    flex-direction: column;
  }

  .diary-editor-actions,
  .diary-complete-button {
    width: 100%;
  }

  .diary-body-field textarea {
    min-height: 320px;
    font-size: 17px;
  }

  .diary-archive-list {
    grid-template-columns: 1fr;
  }
}
</style>
