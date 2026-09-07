const CAT_WORLD_CHILD_COPY_RULES = Object.freeze([
  [/AI Debate/g, "AI 英语辩论"],
  [/完整英语闭环/g, "一次完整学习"],
  [/今日学习闭环已完成/g, "今天的学习全部完成"],
  [/今日学习闭环/g, "今天全部学完"],
  [/学习闭环/g, "完整学习"],
  [/英语闭环/g, "完整学习"],
  [/完整闭环/g, "单词和表达都完成"],
  [/闭环/g, "全部完成"],
  [/输入输出组合/g, "单词和表达都练了"],
  [/输入输出/g, "单词和表达"],
  [/输入和输出/g, "练词和表达"],
  [/词汇输入/g, "词汇学习"],
  [/英语输出/g, "英语表达"],
  [/输出能力/g, "表达能力"],
  [/输出格/g, "表达格"],
  [/输入格/g, "练词格"],
  [/学习触点/g, "学习记录"],
  [/英语触点/g, "英语学习"],
  [/触点/g, "学习记录"],
  [/最近七天学习节奏/g, "最近七天学习"],
  [/七日节奏/g, "七天学习"],
  [/近 7 日节奏/g, "最近 7 天学习"],
  [/学习节奏/g, "学习习惯"],
  [/玩耍节奏/g, "玩耍习惯"],
  [/行动节奏/g, "活动习惯"],
  [/自己的节奏/g, "自己的步子"],
  [/稳定节奏/g, "稳定习惯"],
  [/熟悉节奏/g, "常来学习"],
  [/节奏/g, "步子"],
  [/学习产能/g, "学习能量"],
  [/产能/g, "能量"],
  [/运营活动/g, "特别奖励"],
  [/运营能量/g, "奖励能量"],
  [/三日巩固/g, "三天后再想"],
  [/隔日回想/g, "隔天想一想"],
  [/主动回想/g, "自己想一想"],
  [/巩固复习/g, "再练一遍"],
  [/复盘/g, "再想想"],
  [/今日参数/g, "今天的样子"],
  [/独立状态/g, "今天心情"],
]);

export function friendlyCatWorldText(value = "") {
  return CAT_WORLD_CHILD_COPY_RULES.reduce(
    (text, [pattern, replacement]) => text.replace(pattern, replacement),
    String(value ?? ""),
  );
}

export function friendlyCatWorldData(value) {
  if (typeof value === "string") return friendlyCatWorldText(value);
  if (Array.isArray(value)) return value.map((entry) => friendlyCatWorldData(entry));
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value).map(([key, entry]) => [key, friendlyCatWorldData(entry)]),
  );
}
