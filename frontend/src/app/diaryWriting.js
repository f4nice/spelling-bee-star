export function countDiaryWords(value) {
  return (String(value || "").match(/[A-Za-z]+(?:[-'][A-Za-z]+)*/g) || []).length;
}

export function diaryWordsRemaining(value, minimumWords = 100) {
  return Math.max(Number(minimumWords || 0) - countDiaryWords(value), 0);
}

export function diaryWritingProgress(value, minimumWords = 100) {
  return Math.min(countDiaryWords(value) / Math.max(Number(minimumWords || 0), 1), 1);
}
