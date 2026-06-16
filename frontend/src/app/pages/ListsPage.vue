<script setup>
defineProps([
  "data",
  "uploadOptions",
  "uploadForm",
  "submitUpload",
  "fallbackLetter",
  "go"
]);
</script>

<template>
    <section class="panel lists-tools-panel">
      <div class="lists-tool-card">
        <div class="lists-import-heading"><p class="section-kicker">Import</p><h2>新增单词表</h2></div>
        <form class="home-upload-form lists-import-form" @submit.prevent="submitUpload">
          <input v-model="uploadForm.word_list_name" type="text" placeholder="单词表名称" required>
          <select v-model="uploadForm.word_list_id"><option value="">新建单词表</option><option v-for="list in uploadOptions.word_lists" :key="list.id" :value="list.id">{{ list.name }}</option></select>
          <input type="file" accept=".xlsx,.xlsm,.xltx,.xltm" required @change="uploadForm.file = $event.target.files[0]">
          <button type="submit">上传预览</button>
        </form>
      </div>
      <div class="lists-tool-card">
        <div class="lists-import-heading"><p class="section-kicker">Images</p><h2>批量上传图片</h2><p>按序号或英文名自动匹配单词。</p></div>
        <form action="/lists/batch-images" method="post" enctype="multipart/form-data" class="home-upload-form batch-image-form">
          <select name="word_list_id" required><option value="">选择单词表</option><option v-for="card in data.cards" :key="card.list.id" :value="card.list.id">{{ card.list.name }}</option></select>
          <input type="file" name="image_files" accept="image/*" multiple webkitdirectory directory required>
          <button type="submit">上传匹配</button>
        </form>
      </div>
    </section>
    <section class="word-grid">
      <article v-for="card in data.cards" :key="card.list.id" class="word-card list-card">
        <button class="list-card-link plain-card-button" type="button" @click="go(`/lists/${card.list.id}`)">
          <img v-if="card.cover_word?.image_url" :src="card.cover_word.image_url" :alt="card.list.name"><div v-else class="image-fallback">{{ fallbackLetter(card.cover_word) }}</div>
          <div class="word-card-body"><div class="word-card-title"><strong>{{ card.list.name }}</strong><span class="status">{{ card.count }} 词</span></div></div>
        </button>
        <div class="challenge-card-actions">
          <div class="mini-progress"><span>{{ card.challenge.completed }} / {{ card.challenge.total }}</span><div><i :style="{ width: `${card.challenge.percent}%` }"></i></div></div>
          <button class="challenge-button" type="button" @click="go(`/challenge/${card.list.id}?daily_count=20&start_count=${card.challenge.completed}`)">Vue挑战</button>
        </div>
      </article>
    </section>
</template>
