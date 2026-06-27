export const sidebarNavItems = [
  { label: "首页", path: "/", routes: ["home"] },
  { label: "我的单词表", path: "/lists", routes: ["lists", "listDetail"] },
  { label: "英文小报", path: "/newspaper", routePrefix: "newspaper" },
  { label: "好词好句", path: "/booklearner", routes: ["booklearner", "booklearnerQuotes", "booklearnerUpload", "booklearnerDetail"] },
  { label: "科学探索", path: "/booklearner/science", routes: ["booklearnerScienceHome", "booklearnerScience"] },
  { label: "我的生词本", path: "/wrong-words", routes: ["wrongWords"], countKey: "wrongWordCount" },
];

export function isSidebarNavItemActive(item, route) {
  if (item.routes?.includes(route.name)) return true;
  return Boolean(item.routePrefix && route.name.startsWith(item.routePrefix));
}

export function buildSidebarNavItems({ route, shell }) {
  return sidebarNavItems.map((item) => ({
    ...item,
    active: isSidebarNavItemActive(item, route),
    count: item.countKey ? shell[item.countKey] : undefined,
  }));
}
