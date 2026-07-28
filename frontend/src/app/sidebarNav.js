export const sidebarNavItems = [
  { label: "首页", path: "/", routes: ["home"] },
  { label: "我的单词表", path: "/lists", routes: ["lists", "listDetail"] },
  { label: "我的作文集", path: "/essays", routes: ["essays"] },
  { label: "AI Debate", path: "/debate", routes: ["debate"] },
  { label: "英文小报", path: "/newspaper", routePrefix: "newspaper" },
  { label: "好词好句", path: "/booklearner", routes: ["booklearner", "booklearnerQuotes", "booklearnerUpload", "booklearnerDetail"] },
  { label: "SPB-个人赛冠军词库", path: "/spb", routes: ["spb"], collection: "individual" },
  { label: "我的生词本", path: "/wrong-words", routes: ["wrongWords"], countKey: "wrongWordCount" },
  { label: "猫咪能量世界", path: "/cat-world", routes: ["catWorld"] },
];

export function isSidebarNavItemActive(item, route) {
  if (item.routes?.includes(route.name)) {
    if (!item.collection) return true;
    const routeCollection = route.params?.collection || "individual";
    return routeCollection === item.collection;
  }
  return Boolean(item.routePrefix && route.name.startsWith(item.routePrefix));
}

export function buildSidebarNavItems({ route, shell }) {
  return sidebarNavItems.map((item) => ({
    ...item,
    active: isSidebarNavItemActive(item, route),
    count: item.countKey ? shell[item.countKey] : undefined,
  }));
}
