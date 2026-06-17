import { createApp } from "vue";
import ChallengeApp from "./ChallengeApp.vue";

const root = document.getElementById("speakeasy-challenge-app");

createApp(ChallengeApp, {
  wordListId: Number(root?.dataset.wordListId || 0),
}).mount("#speakeasy-challenge-app");
