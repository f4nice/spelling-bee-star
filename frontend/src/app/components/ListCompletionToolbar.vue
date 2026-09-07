<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { COMPLETION_ACTIVE_STATUSES, createListCompletionController } from "../listCompletionJob.js";

const props = defineProps({
  wordListId: { type: Number, required: true },
  incompleteCount: { type: Number, required: true },
  refreshListDetail: { type: Function, required: true },
});
const state = ref({ job: null, busy: true, notice: "" });
const confirming = ref(false);
const job = computed(() => state.value.job);
const active = computed(() => COMPLETION_ACTIVE_STATUSES.has(job.value?.status));
const progress = computed(() => job.value?.total ? Math.min(100, Math.round(job.value.done / job.value.total * 100)) : 0);
const unresolved = computed(() => (job.value?.results || []).filter(item => ["partial", "failed"].includes(item.status) || (item.status === "skipped" && item.missing_fields?.length)));
const labels = { phonetic: "音标", part_of_speech: "词性", english_definition: "英文释义", chinese_definition: "中文释义", english_example: "英文例句" };
const controller = createListCompletionController({
  onState: next => { state.value = next; },
  onRefresh: id => props.refreshListDetail(id),
});
watch(() => props.wordListId, id => { confirming.value = false; controller.setList(id); }, { immediate: true });
onUnmounted(() => controller.dispose());

async function start() {
  confirming.value = false;
  await controller.start();
}
</script>

<template>
  <section class="list-completion-toolbar" aria-label="批量补全单词">
    <div class="completion-heading">
      <div class="completion-summary">
        <strong>单词补全 <span class="completion-count">待补全 {{ incompleteCount }} 个</span></strong>
        <span>优先小程序，网上词典补缺；保留已有内容和手动锁定项。</span>
      </div>
      <div class="completion-actions">
        <button v-if="active" class="secondary-button" type="button" :disabled="state.busy || job.status === 'stopping'" @click="controller.stop()">
          {{ job.status === 'stopping' ? '正在停止…' : '停止' }}
        </button>
        <button class="primary-action-button completion-start" type="button" :disabled="state.busy || active || !incompleteCount" @click="confirming = true">
          {{ active ? '补全中…' : state.busy ? '请稍候…' : '批量补全' }}
        </button>
      </div>
    </div>
    <div v-if="confirming" class="completion-confirm" role="group" aria-label="确认批量补全">
      <p>补全当前词表的 {{ incompleteCount }} 个未补全单词？仅处理缺项，不生成图片。任务在后台运行，可随时停止。</p>
      <div class="completion-actions">
        <button class="secondary-button" type="button" @click="confirming = false">取消</button>
        <button class="primary-action-button" type="button" @click="start">开始补全</button>
      </div>
    </div>
    <div v-if="job" class="completion-progress" :class="{ 'has-error': job.status === 'failed' }">
      <div class="completion-progress-heading" role="status">
        <span>{{ job.message }}<template v-if="active && job.current_word"> · {{ job.current_word }}</template></span>
        <strong>{{ job.done }} / {{ job.total }}</strong>
      </div>
      <progress :value="job.done" :max="job.total || 1" :aria-label="`补全进度 ${progress}%`"></progress>
      <div class="completion-stats">
        <span>已补全 <b>{{ job.completed }}</b></span>
        <span>仍有缺项 <b>{{ job.partial }}</b></span>
        <span>失败 <b>{{ job.failed }}</b></span>
        <span v-if="job.skipped">跳过 <b>{{ job.skipped }}</b></span>
      </div>
      <details v-if="unresolved.length" class="completion-results">
        <summary>查看未补全的词（{{ unresolved.length }}）</summary>
        <ul>
          <li v-for="item in unresolved" :key="item.word_id">
            <a :href="`/words/${item.word_id}?edit=1&list_id=${wordListId}`">{{ item.word }}</a>
            <span>{{ item.message }}<template v-if="item.missing_fields?.length"> · 缺少{{ item.missing_fields.map(field => labels[field] || field).join('、') }}</template></span>
          </li>
        </ul>
      </details>
    </div>
    <p v-if="state.notice" class="completion-notice" role="status">{{ state.notice }}</p>
  </section>
</template>

<style scoped>
.list-completion-toolbar { margin-top: 12px; padding: 16px; border: 1px solid #bfddd3; border-radius: 16px; background: linear-gradient(120deg, #f0faf5, #f7fafc); }
.completion-heading, .completion-progress-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.completion-summary { display: grid; gap: 7px; color: #356257; font-size: 13px; }
.completion-summary > strong { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; color: #125e49; font-size: 15px; }
.completion-count { padding: 4px 9px; border-radius: 20px; background: #deeee7; font-size: 12px; }
.completion-actions { display: flex; gap: 8px; flex-shrink: 0; }
.completion-start { min-width: 160px; }
.completion-actions button:disabled { opacity: .55; cursor: not-allowed; }
.completion-confirm { border-top: 1px solid #cde0d8; margin-top: 14px; padding-top: 10px; font-size: 14px; }
.completion-confirm p { margin: 0 0 10px; }
.completion-progress { margin-top: 14px; padding-top: 12px; border-top: 1px solid #cde0d8; font-size: 13px; color: #356257; }
.completion-progress-heading strong { white-space: nowrap; }
.completion-progress progress { display: block; width: 100%; height: 8px; margin: 10px 0; border: none; border-radius: 8px; overflow: hidden; background: #e1eae5; accent-color: #168368; }
progress::-webkit-progress-bar { background: #e1eae5; }
progress::-webkit-progress-value { background: #168368; border-radius: 8px; }
.completion-stats { display: flex; gap: 16px; flex-wrap: wrap; }
.completion-results { margin-top: 12px; }
.completion-results summary { cursor: pointer; }
.completion-results ul { max-height: 220px; overflow-y: auto; padding-left: 20px; }
.completion-results li { margin: 8px 0; }
.completion-results a { font-weight: 700; margin-right: 10px; color: #096b56; }
.completion-notice, .has-error { color: #a04b10; }
.completion-notice { margin: 10px 0 0; font-size: 13px; }
@media (max-width: 650px) {
  .completion-heading { align-items: stretch; flex-direction: column; }
  .completion-actions { justify-content: flex-end; }
  .completion-start { flex: 1; }
}
</style>
