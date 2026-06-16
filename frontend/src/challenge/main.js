import { createApp } from 'vue';
import ChallengeApp from './ChallengeApp.vue';

const root = document.getElementById('challenge-vue-app');
createApp(ChallengeApp, {
  wordListId: Number(root?.dataset.wordListId || 0),
}).mount('#challenge-vue-app');
