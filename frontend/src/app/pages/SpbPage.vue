<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});

const rawText = ref("");

function normalizeCell(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function parseLine(line, index) {
  const cells = String(line || "")
    .split(/\t|,|，|\s{2,}/)
    .map(normalizeCell)
    .filter(Boolean);
  const first = cells[0] || normalizeCell(line);
  const match = first.match(/[A-Za-z][A-Za-z' -]*/);
  const word = normalizeCell(match?.[0] || first);
  const meaning = normalizeCell(cells.slice(1).join(" "));
  return {
    id: `${index}-${word}`,
    index: index + 1,
    word,
    meaning,
    source: props.data.collectionName || "SPB",
  };
}

const rows = computed(() =>
  rawText.value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map(parseLine)
    .filter((row) => row.word),
);

const summary = computed(() => {
  const unique = new Set(rows.value.map((row) => row.word.toLowerCase()));
  return {
    rows: rows.value.length,
    unique: unique.size,
  };
});

async function copyTable() {
  const header = ["序号", "单词", "释义", "来源"].join("\t");
  const body = rows.value.map((row) => [row.index, row.word, row.meaning, row.source].join("\t")).join("\n");
  await navigator.clipboard?.writeText([header, body].filter(Boolean).join("\n"));
}

function downloadCsv() {
  const escapeCsv = (value) => `"${String(value || "").replace(/"/g, '""')}"`;
  const header = ["序号", "单词", "释义", "来源"].map(escapeCsv).join(",");
  const body = rows.value
    .map((row) => [row.index, row.word, row.meaning, row.source].map(escapeCsv).join(","))
    .join("\n");
  const blob = new Blob([`\ufeff${[header, body].filter(Boolean).join("\n")}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${props.data.collectionSlug || "spb-word-bank"}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
</script>

<template>
  <section class="spb-page">
    <section class="panel app-page-heading spb-heading">
      <div class="page-heading-title">
        <p class="section-kicker">SpeakEasy</p>
        <h1>SPB</h1>
      </div>
      <span class="spb-target-pill">{{ data.collectionName }}</span>
    </section>

    <section class="panel spb-workbench">
      <div class="spb-workbench-head">
        <div>
          <p class="section-kicker">Word Bank</p>
          <h2>{{ data.collectionName }}</h2>
        </div>
        <div class="spb-actions">
          <button class="secondary-button" type="button" :disabled="!rows.length" @click="copyTable">复制表格</button>
          <button class="secondary-button" type="button" :disabled="!rows.length" @click="downloadCsv">导出 CSV</button>
          <button class="primary-action-button" type="button" @click="go('/upload')">上传导入</button>
        </div>
      </div>

      <div class="spb-import-grid">
        <label class="spb-paste-panel">
          <span>SPB 词库内容</span>
          <textarea
            v-model="rawText"
            spellcheck="false"
            placeholder="粘贴单词、释义或表格内容"
          />
        </label>
        <div class="spb-summary-panel">
          <span>已整理</span>
          <strong>{{ summary.rows }}</strong>
          <em>唯一单词 {{ summary.unique }}</em>
        </div>
      </div>

      <div class="spb-table-wrap">
        <table class="spb-word-table">
          <thead>
            <tr>
              <th>#</th>
              <th>单词</th>
              <th>释义</th>
              <th>来源</th>
            </tr>
          </thead>
          <tbody v-if="rows.length">
            <tr v-for="row in rows" :key="row.id">
              <td>{{ row.index }}</td>
              <td><strong>{{ row.word }}</strong></td>
              <td>{{ row.meaning || "待补充" }}</td>
              <td>{{ row.source }}</td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td colspan="4" class="spb-empty-row">等待词库内容</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
