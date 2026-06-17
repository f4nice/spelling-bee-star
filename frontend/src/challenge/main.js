import { createApp } from "vue";
import ChallengeApp from "./ChallengeApp.vue";
import { readChallengeWordListId } from "./challengeMountContext.js";

const root = document.getElementById("speakeasy-challenge-app");

if (root) {
  createApp(ChallengeApp, {
    wordListId: readChallengeWordListId(root),
  }).mount(root);
}
