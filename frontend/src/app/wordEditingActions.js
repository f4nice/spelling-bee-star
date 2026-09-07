import { fetchJson } from "./utils.js";
import { wordApiPaths } from "./wordApiPaths.js";
import { createWordFieldForm } from "./wordEditingForms.js";

export function createWordEditSnapshot(word) {
  return {
    phonetic: normalizePhonetic(word.phonetic || ""),
    alternate_spellings: word.alternate_spellings || "",
    english_definition: word.english_definition || "",
    chinese_definition: word.chinese_definition || "",
    english_example: word.english_example || "",
  };
}

export function normalizePhonetic(value) {
  return String(value || "").trim().replace(/^\/+|\/+$/g, "").trim();
}

export function isWebsterRespelling(value) {
  return /^韦氏标音\s*[:：]/u.test(normalizePhonetic(value));
}

export function formatPhonetic(value) {
  const text = normalizePhonetic(value);
  return text && !isWebsterRespelling(text) ? `/${text}/` : text;
}

export function canUsePhoneticForAi(value) {
  return Boolean(normalizePhonetic(value)) && !isWebsterRespelling(value);
}

export async function saveWordEditField({ wordId, field, value, setSaving, applySavedValue }) {
  setSaving(field);
  const form = createWordFieldForm({ field, value });
  try {
    const result = await fetchJson(wordApiPaths.field(wordId), { method: "POST", body: form });
    applySavedValue(result.value);
  } finally {
    setSaving("");
  }
}
