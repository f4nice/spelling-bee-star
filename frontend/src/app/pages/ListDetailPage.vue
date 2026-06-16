<script setup>
defineProps([
  "data",
  "renameList",
  "syncListImages",
  "wordVueUrl",
  "imageForWord",
  "fallbackLetter"
]);
</script>

<template>
    <section class="panel upload-panel">
      <div><input v-model="data.word_list.name" class="list-title-input"><p>{{ data.words.length }} 个单词</p></div>
      <div class="list-actions"><button class="secondary-button" type="button" @click="renameList">保存名称</button><a class="ghost-button compact-button" href="/vue/upload">继续导入</a><form :action="`/lists/${data.word_list.id}/delete`" method="post" class="delete-list-form"><input type="password" name="password" placeholder="删除密码" required><button class="danger-button" type="submit">删除</button></form></div>
    </section>
    <section class="panel image-sync-panel">
      <div class="sync-summary"><div class="sync-heading"><strong>图片同步</strong><span v-if="data.sync_job">{{ data.sync_job.done }} / {{ data.sync_job.total }}</span></div><p>{{ data.sync_job?.message || '查找缺失图片，下载并压缩到服务器图片库。' }}</p></div>
      <button class="secondary-button sync-image-button" type="button" @click="syncListImages">同步图片</button>
    </section>
    <section class="word-grid">
      <a v-for="(word, index) in data.words" :key="word.id" class="word-card" :href="wordVueUrl(word, data.word_list.id)">
        <span class="word-index-badge">#{{ index + 1 }}</span><img v-if="imageForWord(word)" :src="word.image_url" :alt="word.word"><div v-else class="image-fallback">{{ fallbackLetter(word) }}</div>
        <div class="word-card-body"><div class="word-card-title"><strong>{{ word.word }}</strong><span class="challenge-result-badges"><span class="challenge-result-badge is-correct">对 {{ word.challenge_stats.correct }}</span><span class="challenge-result-badge is-wrong">错 {{ word.challenge_stats.wrong }}</span></span></div><p>{{ word.chinese_definition || word.english_definition || '等待补全' }}</p></div>
      </a>
    </section>
</template>
