export function countDiaryCharacters(value) {
  return (String(value || "").match(/[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/g) || []).length;
}

export function diaryCharactersRemaining(value, minimumCharacters = 100) {
  return Math.max(Number(minimumCharacters || 0) - countDiaryCharacters(value), 0);
}

export function diaryWritingProgress(value, minimumCharacters = 100) {
  return Math.min(countDiaryCharacters(value) / Math.max(Number(minimumCharacters || 0), 1), 1);
}
