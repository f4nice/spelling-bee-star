export function parseRoute(pathname = window.location.pathname) {
  const path = pathname.replace(/\/$/, "").replace(/^\//, "");
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
