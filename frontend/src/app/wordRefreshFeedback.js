const REQUIRED_TEXT = [
  ["phonetic", "音标"],
  ["english_definition", "英文定义"],
  ["chinese_definition", "中文定义"],
  ["english_example", "英文例句"],
];

export function wordRefreshFeedback(result) {
  if (result?.ok === false) throw new Error("服务器未能完成本次补全，现有内容不会被清除。");
  const word = result?.word;
  if (!word) throw new Error("未收到补全结果，现有内容不会被清除。");

  const missing = REQUIRED_TEXT
    .filter(([key]) => !String(word[key] || "").trim())
    .map(([, label]) => label);
  const hasContent = missing.length < REQUIRED_TEXT.length;
  const sourceFailed = word.enrichment_status === "failed" || Boolean(word.enrichment_error);

  // A returned snapshot can still be pending; never label it a finished failure.
  if (word.enrichment_status === "pending") {
    return {
      status: "pending", failed: false,
      notice: `后台仍在补全，${hasContent ? "现有内容已保存" : "暂未返回词条内容"}。请稍后查看结果。`,
    };
  }
  if (!missing.length) {
    return {
      status: "complete", failed: sourceFailed,
      notice: sourceFailed
        ? "词条主要内容已齐全并保存。本次查询未完全成功，已有内容未受影响。"
        : "补全完成，词条已更新。",
    };
  }
  if (hasContent) {
    return {
      status: "partial", failed: false,
      notice: `现有内容已保存，仍缺${missing.join("、")}。${sourceFailed ? "本次查询未完全成功" : "当前词库未返回这些内容"}，可双击字段手动补充。`,
    };
  }
  return {
    status: "failed", failed: true,
    notice: `本次未获取到可用的词条内容，仍缺${missing.join("、")}。词库可能未收录或暂不可用，可双击字段手动填写。`,
  };
}
