function stripQuery(value = "") {
  return String(value || "").split("?", 1)[0].split("#", 1)[0];
}

function filenameFromUrl(url = "") {
  const raw = stripQuery(url);
  if (!raw) return "";
  try {
    const path = raw.includes("://") ? new URL(raw).pathname : raw;
    const name = path.split(/[\\/]/).filter(Boolean).pop() || "";
    return decodeURIComponent(name);
  } catch {
    return raw.split(/[\\/]/).filter(Boolean).pop() || "";
  }
}

function includesAny(text, tokens) {
  return tokens.some((token) => text.includes(token));
}

function normalizeMeta(meta = {}, fallbackUrl = "", rules = [], emptyLabel = "暂无来源") {
  const source = String(meta?.source || "").trim();
  const filename = meta?.filename || filenameFromUrl(fallbackUrl);
  const combined = `${source} ${filename} ${fallbackUrl}`.toLowerCase();
  const existingPrefix = String(meta?.prefix || "").trim();
  const existingLabel = String(meta?.label || "").trim();
  if (existingPrefix && existingLabel) {
    return { source, filename, prefix: existingPrefix, label: existingLabel };
  }
  if (!fallbackUrl && !filename && !source) {
    return { source, filename, prefix: "未配置", label: emptyLabel };
  }
  const matched = rules.find((rule) => rule.match(combined, source.toLowerCase(), filename.toLowerCase()));
  if (matched) {
    return { source, filename, prefix: matched.prefix, label: matched.label };
  }
  return {
    source,
    filename,
    prefix: fallbackUrl ? "未知" : "未配置",
    label: fallbackUrl ? "来源未知" : emptyLabel,
  };
}

const audioRules = [
  {
    prefix: "SPB",
    label: "SPB小程序",
    match: (combined, source, filename) => source.startsWith("spb") || filename.startsWith("spb-") || combined.includes("-spb-") || combined.includes("miniprogram"),
  },
  {
    prefix: "AI",
    label: "AI生成",
    match: (combined, source, filename) => source.startsWith("ai") || filename.startsWith("ai-") || includesAny(combined, ["ai-tts", "aliyun", "dashscope", "phoneme"]),
  },
  {
    prefix: "词典",
    label: "词典音源",
    match: (combined, source, filename) => source.startsWith("dictionary") || filename.startsWith("dict-") || includesAny(combined, ["youdao", "free-dictionary", "google", "tts"]),
  },
  {
    prefix: "录音",
    label: "本地录音",
    match: (combined, source, filename) => source.startsWith("record") || filename.startsWith("record-"),
  },
  {
    prefix: "上传",
    label: "上传音频",
    match: (combined, source, filename) => source.startsWith("upload") || filename.startsWith("upload-") || combined.includes("upload"),
  },
  {
    prefix: "本地",
    label: "服务器音频",
    match: (combined) => combined.includes("/media/audio/"),
  },
  {
    prefix: "外链",
    label: "外链音频",
    match: (combined) => combined.includes("http://") || combined.includes("https://"),
  },
];

const imageRules = [
  {
    prefix: "SPB",
    label: "SPB图片",
    match: (combined, source, filename) => source.startsWith("spb") || filename.startsWith("spb-") || combined.includes("-spb-") || combined.includes("miniprogram"),
  },
  {
    prefix: "AI",
    label: "AI生成图",
    match: (combined, source, filename) => source.startsWith("ai") || filename.startsWith("ai-") || includesAny(combined, ["ai-image", "generated", "dashscope", "qwen", "wan"]),
  },
  {
    prefix: "上传",
    label: "上传图片",
    match: (combined, source, filename) => source.startsWith("upload") || filename.startsWith("upload-") || combined.includes("upload"),
  },
  {
    prefix: "网络",
    label: "网络选图",
    match: (combined, source) => source.startsWith("network") || combined.includes("http://") || combined.includes("https://"),
  },
  {
    prefix: "本地",
    label: "服务器图片",
    match: (combined) => combined.includes("/media/images/") || combined.includes("/media/generated-assets/"),
  },
];

export function inferAudioSourceMeta(meta = {}, url = "") {
  return normalizeMeta(meta, url, audioRules, "暂无音频");
}

export function inferImageSourceMeta(meta = {}, url = "") {
  return normalizeMeta(meta, url, imageRules, "暂无图片");
}

export function sourceText(meta = {}) {
  const prefix = String(meta.prefix || "").trim();
  const label = String(meta.label || "").trim();
  if (prefix && label && prefix !== label) return `${prefix} · ${label}`;
  return label || prefix || "来源未知";
}
