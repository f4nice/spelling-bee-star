<script setup>
defineProps([
  "data",
  "wordEdit",
  "imageCandidates",
  "audioOptions",
  "recorderState",
  "uploadWordImage",
  "findImages",
  "chooseNetworkImage",
  "wordNavUrl",
  "saveWordField",
  "refreshWord",
  "playAudio",
  "fetchAudioOptions",
  "startRecording",
  "chooseAudio",
  "stopRecording",
  "saveRecording",
  "fallbackLetter"
]);
</script>

<template>
    <section class="detail-layout">
      <div class="detail-media-panel">
        <div class="detail-media"><span v-if="data.navigation.index" class="word-index-badge">#{{ data.navigation.index }}</span><img v-if="data.word.image_url" :src="data.word.image_url" :alt="data.word.word"><div v-else class="image-fallback large">{{ fallbackLetter(data.word) }}</div></div>
        <div v-if="data.can_edit" class="image-replace-form">
          <label>替换图片 <input type="file" accept="image/*" @change="$event.target.files[0] && uploadWordImage($event.target.files[0])"></label>
          <button type="button" class="secondary-button" @click="findImages">网络找图</button>
          <span v-if="data.word.image_locked" class="lock-badge">已锁定</span>
        </div>
        <div v-if="imageCandidates.length" class="image-picker-grid inline-image-grid">
          <button v-for="(item, index) in imageCandidates" :key="item.url" type="button" class="image-picker-option" @click="chooseNetworkImage(item.url)"><img :src="item.url" :alt="`候选图 ${index + 1}`"><span>{{ item.source || '网络图片' }}</span></button>
        </div>
      </div>
      <article class="panel detail-panel">
        <div class="detail-study-row"><div class="auto-study-controls"><a class="secondary-button" :href="wordNavUrl(data.navigation.previous_word_id)">上一个</a><a class="secondary-button" :href="wordNavUrl(data.navigation.next_word_id)">下一个</a></div></div>
        <div class="detail-heading"><div class="word-title-stack"><h1>{{ data.word.word }}</h1><p v-if="data.word.phonetic" class="phonetic">/{{ data.word.phonetic }}/</p><textarea v-if="data.can_edit" v-model="wordEdit.alternate_spellings" class="inline-edit-input" @blur="saveWordField('alternate_spellings')"></textarea><strong v-else>{{ data.word.alternate_spellings || '暂无' }}</strong></div><div class="detail-heading-actions"><button v-if="data.can_edit" type="button" @click="refreshWord">重新补全</button></div></div>
        <div class="audio-row">
          <label v-for="accent in ['us','gb']" :key="accent">{{ accent === 'us' ? '美式发音' : '英式发音' }}
            <div class="audio-actions"><button type="button" class="secondary-button" @click="playAudio(`audio-${accent}`)">朗读{{ accent === 'us' ? '美式' : '英式' }}</button><audio :id="`audio-${accent}`" controls preload="none" :src="data.audio_sources[accent]"></audio><button v-if="data.can_edit" type="button" class="secondary-button" @click="fetchAudioOptions(accent)">重新获取音频</button><button v-if="data.can_edit" type="button" class="secondary-button" @click="startRecording(accent)">录制音源</button></div>
            <div v-if="audioOptions[accent]?.length" class="audio-options"><div v-for="option in audioOptions[accent]" :key="option.url" class="audio-option"><strong>{{ option.label }}</strong><audio controls :src="option.url"></audio><button type="button" class="secondary-button" @click="chooseAudio(accent, option.url)">选这个</button></div></div>
          </label>
        </div>
        <div v-if="recorderState.status" class="record-audio-panel"><p>{{ recorderState.status }}</p><button type="button" class="secondary-button" @click="stopRecording">停止录音</button><audio v-if="recorderState.preview" controls :src="recorderState.preview"></audio><button v-if="recorderState.blob" type="button" @click="saveRecording">确认替换</button></div>
        <dl class="definition-list">
          <dt>词性</dt><dd>{{ data.word.part_of_speech || '暂无' }}</dd>
          <dt>英文定义</dt><dd><textarea v-if="data.can_edit" v-model="wordEdit.english_definition" @blur="saveWordField('english_definition')"></textarea><span v-else>{{ data.word.english_definition || '暂无' }}</span></dd>
          <dt>中文定义</dt><dd><textarea v-if="data.can_edit" v-model="wordEdit.chinese_definition" @blur="saveWordField('chinese_definition')"></textarea><span v-else>{{ data.word.chinese_definition || '暂无' }}</span></dd>
          <dt>英文例句</dt><dd><textarea v-if="data.can_edit" v-model="wordEdit.english_example" @blur="saveWordField('english_example')"></textarea><span v-else>{{ data.word.english_example || '暂无' }}</span></dd>
          <dt>来源</dt><dd>{{ data.word.source || '暂无' }}</dd>
        </dl>
        <div v-if="data.word.enrichment_error" class="error-box">{{ data.word.enrichment_error }}</div>
      </article>
    </section>
</template>
