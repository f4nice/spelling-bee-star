export function countEssayWords(value) {
  return (String(value || "").normalize("NFC").match(/[A-Za-z\u00c0-\u02af\u1e00-\u1eff]+(?:[-'\u2019][A-Za-z\u00c0-\u02af\u1e00-\u1eff]+)*/g) || []).length;
}

export function essayMinimumWords(essayType) {
  return ["gaokao", "pet"].includes(essayType) ? 100 : 0;
}

export function essayEnergyLimit(body, essayType = "free") {
  return essayMinimumWords(essayType) || countEssayWords(body) >= 100 ? 500 : 200;
}

export function essaySubmissionError(body, essayType = "free") {
  const count = countEssayWords(body);
  const minimum = essayMinimumWords(essayType);
  if (!minimum || count >= minimum) return "";
  const label = essayType === "gaokao" ? "高考" : "PET";
  return `${label}写作至少需要 ${minimum} 个英文单词，当前 ${count} 词，还差 ${minimum - count} 词。`;
}
