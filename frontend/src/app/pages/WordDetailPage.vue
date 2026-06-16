<script setup>
import WordAudioPanel from "../components/WordAudioPanel.vue";
import WordDefinitionList from "../components/WordDefinitionList.vue";
import WordMediaPanel from "../components/WordMediaPanel.vue";

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
    <WordMediaPanel
      :data="data"
      :image-candidates="imageCandidates"
      :fallback-letter="fallbackLetter"
      :upload-word-image="uploadWordImage"
      :find-images="findImages"
      :choose-network-image="chooseNetworkImage"
    />

    <article class="panel detail-panel">
      <div class="detail-study-row">
        <div class="auto-study-controls">
          <a class="secondary-button" :href="wordNavUrl(data.navigation.previous_word_id)">上一个</a>
          <a class="secondary-button" :href="wordNavUrl(data.navigation.next_word_id)">下一个</a>
        </div>
      </div>

      <div class="detail-heading">
        <div class="word-title-stack">
          <h1>{{ data.word.word }}</h1>
          <p v-if="data.word.phonetic" class="phonetic">/{{ data.word.phonetic }}/</p>
          <textarea
            v-if="data.can_edit"
            v-model="wordEdit.alternate_spellings"
            class="inline-edit-input"
            @blur="saveWordField('alternate_spellings')"
          ></textarea>
          <strong v-else>{{ data.word.alternate_spellings || '暂无' }}</strong>
        </div>
        <div class="detail-heading-actions">
          <button v-if="data.can_edit" type="button" @click="refreshWord">重新补全</button>
        </div>
      </div>

      <WordAudioPanel
        :data="data"
        :audio-options="audioOptions"
        :recorder-state="recorderState"
        :play-audio="playAudio"
        :fetch-audio-options="fetchAudioOptions"
        :start-recording="startRecording"
        :choose-audio="chooseAudio"
        :stop-recording="stopRecording"
        :save-recording="saveRecording"
      />

      <WordDefinitionList :data="data" :word-edit="wordEdit" :save-word-field="saveWordField" />
      <div v-if="data.word.enrichment_error" class="error-box">{{ data.word.enrichment_error }}</div>
    </article>
  </section>
</template>
