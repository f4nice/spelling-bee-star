export function parseRoute(pathname = window.location.pathname) {
  const path = pathname.replace(/^\/vue\/?/, "").replace(/\/$/, "");
  const parts = path ? path.split("/") : [];
  if (!parts.length) return { name: "home", params: {} };
  if (parts[0] === "lists" && parts[1]) return { name: "listDetail", params: { id: Number(parts[1]) } };
  if (parts[0] === "lists") return { name: "lists", params: {} };
  if (parts[0] === "wrong-words") return { name: "wrongWords", params: {} };
  if (parts[0] === "challenge-calendar" && parts[1]) return { name: "challengeDay", params: { day: parts[1] } };
  if (parts[0] === "challenge" && parts[1]) return { name: "challenge", params: { id: Number(parts[1]) } };
  if (parts[0] === "words" && parts[1]) return { name: "wordDetail", params: { id: Number(parts[1]) } };
  if (parts[0] === "upload" && parts[1] === "preview" && parts[2]) return { name: "preview", params: { id: parts[2] } };
  if (parts[0] === "upload") return { name: "upload", params: {} };
  if (parts[0] === "newspaper" && parts[1] && parts[2]) return { name: "newspaperArticle", params: { section: parts[1], index: Number(parts[2]) } };
  if (parts[0] === "newspaper") return { name: "newspaper", params: {} };
  if (parts[0] === "booklearner" && parts[1] === "upload") return { name: "booklearnerUpload", params: {} };
  if (parts[0] === "booklearner" && parts[1] === "quotes") return { name: "booklearnerQuotes", params: {} };
  if (parts[0] === "booklearner" && parts[1] === "detail" && parts[2]) return { name: "booklearnerDetail", params: { id: Number(parts[2]) } };
  if (parts[0] === "booklearner") return { name: "booklearner", params: {} };
  return { name: "home", params: {} };
}

export function routeTitle(route, data) {
  if (route.name === "lists") return "我的单词表";
  if (route.name === "listDetail") return data?.word_list?.name || "单词表";
  if (route.name === "wrongWords") return "我的生词本";
  if (route.name === "challengeDay") return `${route.params.day} 挑战词汇`;
  if (route.name === "challenge") return "Vue 挑战";
  if (route.name === "wordDetail") return data?.word?.word || "单词详情";
  if (route.name === "upload") return "导入单词";
  if (route.name === "preview") return "导入预览";
  if (route.name === "newspaper") return "英文小报";
  if (route.name === "newspaperArticle") return data?.article?.title || "英文小报";
  if (route.name.startsWith("booklearner")) return "好词好句";
  return "今天从这里开始";
}

export function oldPathFor(path) {
  return path.replace(/^\/vue/, "") || "/";
}
