<script setup>
defineProps([
  "data",
  "importForm",
  "go",
  "changePreviewSheet",
  "setAllRows",
  "setAllColumns",
  "submitImport"
]);
</script>

<template>
    <section class="panel preview-panel">
      <div class="preview-heading"><div><h1>导入预览</h1><p>{{ data.preview.filename }} · {{ data.preview.rows.length }} 行 · {{ data.preview.columns.length }} 列</p></div><button class="ghost-button" type="button" @click="go('/upload')">重新选择文件</button></div>
      <div class="import-toolbar">
        <label>单词表名称 <input v-model="importForm.word_list_name" required></label>
        <label>Sheet <select v-if="data.preview.sheet_names?.length > 1" :value="data.preview.sheet_name" @change="changePreviewSheet($event.target.value)"><option v-for="sheet in data.preview.sheet_names" :key="sheet" :value="sheet">{{ sheet }}</option></select><input v-else :value="data.preview.sheet_name || 'Sheet1'" disabled></label>
        <button type="button" class="secondary-button" @click="setAllRows(true)">全选行</button><button type="button" class="secondary-button" @click="setAllRows(false)">取消行</button><button type="button" class="secondary-button" @click="setAllColumns(true)">全选列</button><button type="button" class="secondary-button" @click="setAllColumns(false)">取消列</button>
        <label>批量图片 <input type="file" accept="image/*" multiple webkitdirectory directory @change="importForm.image_files = Array.from($event.target.files || [])"></label>
        <button type="button" @click="submitImport">确认导入</button>
      </div>
      <div class="word-column-options"><label v-for="column in data.preview.columns" :key="column" class="word-column-option"><input v-model="importForm.word_columns" type="checkbox" :value="column"><span>{{ column }}</span></label></div>
      <div class="table-wrap"><table class="preview-table"><thead><tr><th>导入</th><th>Excel 行</th><th v-for="column in data.preview.columns" :key="column"><label class="check-label"><input v-model="importForm.selected_columns" type="checkbox" :value="column"><span>{{ column }}</span></label></th></tr></thead><tbody><tr v-for="row in data.preview.rows" :key="row.index"><td><input v-model="importForm.selected_rows" type="checkbox" :value="row.index"></td><td>{{ row.excel_row }}</td><td v-for="column in data.preview.columns" :key="column">{{ row.values[column] || '' }}</td></tr></tbody></table></div>
    </section>
</template>
