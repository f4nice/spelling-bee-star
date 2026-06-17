export function readChallengeWordListId(root = document.getElementById("speakeasy-challenge-app")) {
  return Number(root?.dataset.wordListId || 0);
}
