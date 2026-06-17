export function routeTitle(route, data) {
  if (route.name === "lists") return "我的单词表";
  if (route.name === "listDetail") return data?.word_list?.name || "单词表";
  if (route.name === "wrongWords") return "我的生词本";
  if (route.name === "challengeDay") return `${route.params.day} 挑战词汇`;
  if (route.name === "challenge") return "拼写挑战";
  if (route.name === "wordDetail") return data?.word?.word || "单词详情";
  if (route.name === "upload") return "导入单词";
  if (route.name === "preview") return "导入预览";
  if (route.name === "newspaper") return "英文小报";
  if (route.name === "newspaperArticle") return data?.article?.title || "英文小报";
  if (route.name.startsWith("booklearner")) return "好词好句";
  return "今天从这里开始";
}
