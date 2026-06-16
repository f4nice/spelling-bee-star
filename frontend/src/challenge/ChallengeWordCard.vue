<script setup>
const spelling = defineModel('spelling', { type: String, default: '' });

defineProps({
  state: {
    type: Object,
    required: true,
  },
  submitting: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['submit', 'strip-digits']);

function playAudio(id) {
  const audio = document.getElementById(id);
  if (!audio) return;
  audio.load();
  audio.currentTime = 0;
  audio.play().catch(() => {
    audio.controls = true;
  });
}
</script>

<template>
  <div class="challenge-card">
    <div class="challenge-word-media">
      <img v-if="state.challenge_image_url" :src="state.challenge_image_url" alt="challenge image">
      <div v-else class="image-fallback large">?</div>
    </div>
    <div class="challenge-word-body">
      <p class="challenge-count">第 {{ state.progress.current_index + 1 }} 个 / 共 {{ state.challenge.total }} 个</p>
      <h2 class="spelling-prompt">请拼写这个单词</h2>
      <p v-if="state.current_word.phonetic" class="phonetic">/{{ state.current_word.phonetic }}/</p>

      <div class="challenge-audio-row">
        <label>
          美式发音
          <div class="challenge-audio-actions">
            <button type="button" class="secondary-button" @click="playAudio('challenge-audio-us')">朗读美式</button>
            <audio id="challenge-audio-us" controls controlsList="nodownload" preload="none" :src="state.challenge_audio_sources.us"></audio>
          </div>
        </label>
        <label>
          英式发音
          <div class="challenge-audio-actions">
            <button type="button" class="secondary-button" @click="playAudio('challenge-audio-gb')">朗读英式</button>
            <audio id="challenge-audio-gb" controls controlsList="nodownload" preload="none" :src="state.challenge_audio_sources.gb"></audio>
          </div>
        </label>
      </div>

      <dl class="definition-list compact">
        <dt>词性</dt><dd>{{ state.current_word.part_of_speech || '暂无' }}</dd>
        <dt>英文定义</dt><dd>{{ state.current_word.english_definition || '暂无' }}</dd>
        <dt>中文定义</dt><dd>{{ state.current_word.chinese_definition || '暂无' }}</dd>
        <template v-if="state.masked_example">
          <dt>英文例句</dt><dd>{{ state.masked_example }}</dd>
        </template>
      </dl>

      <form class="spelling-form" @submit.prevent="emit('submit')">
        <label>
          输入拼写
          <input
            v-model="spelling"
            type="text"
            autocomplete="off"
            autocapitalize="none"
            spellcheck="false"
            inputmode="text"
            autofocus
            required
            @input="emit('strip-digits')"
          >
        </label>
        <button type="submit" :disabled="submitting">{{ submitting ? '提交中' : '提交' }}</button>
      </form>
    </div>
  </div>
</template>
