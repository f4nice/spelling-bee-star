<script setup>
import { computed } from "vue";
import {
  importPreviewJobPercent,
  importPreviewStageLabel,
  isImportPreviewJobActive,
} from "../importPreviewJob.js";

const props = defineProps({
  job: {
    type: Object,
    required: true,
  },
});

const percent = computed(() => importPreviewJobPercent(props.job));
const stageLabel = computed(() => importPreviewStageLabel(props.job));
const isActive = computed(() => isImportPreviewJobActive(props.job));
</script>

<template>
  <section
    class="import-preview-progress"
    :class="{
      'is-active': isActive,
      'is-complete': job.status === 'complete',
      'has-error': job.status === 'failed',
    }"
    aria-live="polite"
  >
    <header>
      <div>
        <span>{{ stageLabel }}</span>
        <strong>{{ percent }}%</strong>
      </div>
      <b>{{ job.processed || 0 }} / {{ job.total || 0 }} 个单词</b>
    </header>
    <progress :value="percent" max="100">{{ percent }}%</progress>
    <footer>
      <span>{{ job.message }}</span>
      <span v-if="job.total_lists">
        分表 {{ job.completed_lists || 0 }} / {{ job.total_lists }}
        <template v-if="isActive && job.current_list"> · 当前第 {{ job.current_list }} 个</template>
      </span>
    </footer>
  </section>
</template>
