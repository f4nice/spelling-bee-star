<script setup>
import { computed, onMounted, ref } from 'vue';

const props = defineProps({
  wordListId: {
    type: Number,
    default: null,
  },
});

const root = document.getElementById('challenge-vue-app');
const wordListId = Number(props.wordListId || root?.dataset.wordListId || 0);
const initialParams = new URLSearchParams(window.location.search);

const state = ref(null);
const spelling = ref('');
const loading = ref(true);
const submitting = ref(false);
const errorMessage = ref('');

const query = computed(() => {
  const params = new URLSearchParams();
  params.set('daily_count', String(state.value?.today_challenge?.daily_count || initialParams.get('daily_count') || 20));
  params.set('start_count', String(state.value?.today_challenge?.start_count || initialParams.get('start_count') || 0));
  params.set('session_correct', String(state.value?.today_challenge?.correct || 0));
  params.set('session_wrong', String(state.value?.today_challenge?.wrong || 0));
  const wrongDate = state.value?.wrong_date || initialParams.get('wrong_date');
  if (wrongDate) params.set('wrong_date', wrongDate);
  return params;
});

async function loadState(params = initialParams) {
  loading.value = true;
  errorMessage.value = '';
  try {
    const response = await fetch(`/api/challenge/${wordListId}/state?${params.toString()}`);
    if (!response.ok) throw new Error('加载挑战失败');
    state.value = await response.json();
    spelling.value = '';
  } catch (error) {
    errorMessage.value = error.message || '加载挑战失败';
  } finally {
    loading.value = false;
  }
}

async function submitSpelling() {
  if (!spelling.value.trim() || submitting.value) return;
  submitting.value = true;
  errorMessage.value = '';
  const form = new FormData();
  form.append('action', 'spell');
  form.append('daily_count', String(state.value.today_challenge.daily_count));
  form.append('start_count', String(state.value.today_challenge.start_count));
  form.append('session_correct', String(state.value.today_challenge.correct));
  form.append('session_wrong', String(state.value.today_challenge.wrong));
  form.append('spelling', spelling.value);
  if (state.value.wrong_date) form.append('wrong_date', state.value.wrong_date);
  try {
    const response = await fetch(`/api/challenge/${wordListId}/answer`, {
      method: 'POST',
      body: form,
    });
    if (!response.ok) throw new Error('提交失败');
    const result = await response.json();
    const nextParams = new URLSearchParams(result.query);
    history.replaceState(null, '', `${window.location.pathname}?${nextParams.toString()}`);
    await loadState(nextParams);
  } catch (error) {
    errorMessage.value = error.message || '提交失败';
  } finally {
    submitting.value = false;
  }
}

function stripDigits() {
  spelling.value = spelling.value.replace(/[0-9]/g, '');
}

function playAudio(id) {
  const audio = document.getElementById(id);
  if (!audio) return;
  audio.load();
  audio.currentTime = 0;
  audio.play().catch(() => {
    audio.controls = true;
  });
}

function legacyChallengeUrl(extra = '') {
  return `/challenge/${wordListId}${extra}`;
}

onMounted(() => loadState());
</script>

<template>
  <section class="panel challenge-panel vue-challenge-panel">
    <div v-if="loading" class="empty-state">正在加载挑战...</div>
    <div v-else-if="errorMessage" class="error-box">{{ errorMessage }}</div>
    <template v-else-if="state">
      <div class="challenge-top">
        <div>
          <p class="section-kicker">Vue Challenge</p>
          <h1>{{ state.word_list.name }}</h1>
          <p>
            总进度 {{ state.challenge.completed }} / {{ state.challenge.total }}
            · 今日目标 {{ state.today_challenge.done }} / {{ state.today_challenge.total }}
          </p>
        </div>
        <a class="ghost-button" :href="`/lists/${wordListId}`">返回单词表</a>
      </div>

      <div class="challenge-large-progress">
        <span :style="{ width: `${state.today_challenge.percent}%` }"></span>
      </div>

      <div class="challenge-stats">
        <div><span>本组一共</span><strong>{{ state.today_challenge.total }}</strong><span>个</span></div>
        <div><span>已答</span><strong>{{ state.today_challenge.answered }}</strong><span>个</span></div>
        <div><span>剩余</span><strong>{{ state.today_challenge.remaining }}</strong><span>个</span></div>
        <div><span>本次正确</span><strong class="result-correct">{{ state.today_challenge.correct }}</strong><span>个</span></div>
        <div><span>本次错误</span><strong class="result-wrong">{{ state.today_challenge.wrong }}</strong><span>个</span></div>
      </div>

      <div v-if="state.current_word" class="challenge-card">
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

          <form class="spelling-form" @submit.prevent="submitSpelling">
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
                @input="stripDigits"
              >
            </label>
            <button type="submit" :disabled="submitting">{{ submitting ? '提交中' : '提交' }}</button>
          </form>
        </div>
      </div>

      <div v-else class="challenge-complete">
        <h2>{{ state.today_challenge.all_complete ? '你怎么如此优秀，整组都拿下了' : '今日目标完成了' }}</h2>
        <div class="challenge-result-grid">
          <div><span>本次挑战</span><strong>{{ state.today_challenge.answered }} / {{ state.today_challenge.total }}</strong></div>
          <div><span>答对</span><strong class="result-correct">{{ state.today_challenge.correct }}</strong></div>
          <div><span>答错</span><strong class="result-wrong">{{ state.today_challenge.wrong }}</strong></div>
          <div><span>正确率</span><strong>{{ state.today_challenge.accuracy }}%</strong></div>
        </div>
        <div class="challenge-complete-actions">
          <a class="secondary-button" :href="legacyChallengeUrl(`?daily_count=20&start_count=0`)">回到原挑战页</a>
        </div>
      </div>
    </template>
  </section>
</template>
