<script setup>
import { ref } from "vue";
import { wordRefreshFeedback } from "../wordRefreshFeedback.js";

const props = defineProps({
  canEdit: {
    type: Boolean,
    required: true,
  },
  refreshWord: {
    type: Function,
    required: true,
  },
});

const refreshing = ref(false);
const notice = ref("");
const failed = ref(false);

async function completeWord() {
  if (refreshing.value) return;
  refreshing.value = true;
  failed.value = false;
  notice.value = "正在查询词库并补全，可能需要几十秒…";
  try {
    const result = await props.refreshWord();
    const feedback = wordRefreshFeedback(result);
    failed.value = feedback.failed;
    notice.value = feedback.notice;
  } catch (error) {
    failed.value = true;
    notice.value = `补全失败：${error?.message || "连接暂不可用，请稍后重试。"}`;
  } finally {
    refreshing.value = false;
  }
}
</script>

<template>
  <div class="detail-heading-actions">
    <button v-if="canEdit" type="button" :disabled="refreshing" :aria-busy="refreshing" @click="completeWord">{{ refreshing ? "正在补全…" : "补全当前词" }}</button>
    <p v-if="notice" class="word-refresh-notice" :class="{ 'is-error': failed }" role="status" aria-live="polite">{{ notice }}</p>
  </div>
</template>

<style scoped>
.detail-heading-actions { flex-wrap: wrap; justify-content: flex-end; }
.word-refresh-notice { flex-basis: 100%; max-width: 300px; margin: 8px 0 0; font-size: 13px; line-height: 1.6; color: #176b51; }
.word-refresh-notice.is-error { color: #a15420; }
</style>
