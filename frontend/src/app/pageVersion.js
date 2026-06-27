import { normalizeVersionMatrix } from "./versionInfo.js";

const ROUTE_MODULES = [
  { names: ["home"], key: "home", label: "首页" },
  { names: ["lists", "listDetail", "wordDetail"], key: "word-lists", label: "我的单词表" },
  { names: ["upload", "preview"], key: "upload-import", label: "上传导入" },
  { prefix: "newspaper", key: "newspaper", label: "英文小报" },
  { names: ["booklearnerScienceHome", "booklearnerScience"], key: "science-discovery", label: "科学探索" },
  { prefix: "booklearner", key: "booklearner", label: "好词好句" },
  { names: ["wrongWords"], key: "wrong-words", label: "我的生词本" },
  { names: ["challenge", "challengeDay"], key: "challenge", label: "挑战进度" },
];

export function moduleForRoute(route) {
  const routeName = route?.name || "home";
  return (
    ROUTE_MODULES.find((item) => item.names?.includes(routeName) || (item.prefix && routeName.startsWith(item.prefix))) ||
    ROUTE_MODULES[0]
  );
}

export function versionForLabel(versionMatrix, label) {
  const matrix = normalizeVersionMatrix(versionMatrix);
  const module = (matrix.modules || []).find((item) => item.label === label);
  return module?.version || matrix.pageVersion || "v20260624.0";
}

export function pageVersionForRoute(route, versionMatrix) {
  const module = moduleForRoute(route);
  const version = versionForLabel(versionMatrix, module.label);
  return {
    key: module.key,
    label: module.label,
    version,
    text: `${module.label} ${version}`,
  };
}
