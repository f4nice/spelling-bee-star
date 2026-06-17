<script setup>
import WordDetailPage from '../pages/WordDetailPage.vue';

defineProps({
  ctx: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <WordDetailPage
    :data="ctx.data"
    :word-edit="ctx.wordEdit"
    :image-candidates="ctx.imageCandidates"
    :audio-options="ctx.audioOptions"
    :recorder-state="ctx.recorderState"
    :upload-word-image="ctx.uploadWordImage"
    :find-images="ctx.findImages"
    :choose-network-image="ctx.chooseNetworkImage"
    :image-for-word="ctx.imageForWord"
    :word-nav-url="ctx.wordNavUrl"
    :save-word-field="ctx.saveWordField"
    :refresh-word="ctx.refreshWord"
    :play-audio="ctx.playAudio"
    :fetch-audio-options="ctx.fetchAudioOptions"
    :start-recording="ctx.startRecording"
    :choose-audio="ctx.chooseAudio"
    :stop-recording="ctx.stopRecording"
    :save-recording="ctx.saveRecording"
  />
</template>
