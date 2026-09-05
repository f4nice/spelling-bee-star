<script setup>
import { ref } from "vue";

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
    const word = result?.word;
    if (!word) throw new Error("未收到补全结果，请稍后重试。");
    const missing = [["phonetic", "音标"], ["english_definition", "英文定义"], ["chinese_definition", "中文定义"], ["english_example", "英文例句"]]
      .filter(([key]) => !String(word[key] || "").trim()).map(([, label]) => label);
    failed.value = missing.length > 0;
    notice.value = missing.length
      ? `本次未能补齐${missing.join("、")}。词库可能暂无内容或服务暂不可用，请稍后重试，也可双击字段手动填写。`
      : "补全完成，词条已更新。";
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
