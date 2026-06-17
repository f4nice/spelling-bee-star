export const sidebarNavItems = [
  { label: "首页", path: "/", routes: ["home"] },
  { label: "我的单词表", path: "/lists", routes: ["lists", "listDetail"] },
  { label: "英文小报", path: "/newspaper", routePrefix: "newspaper" },
  { label: "好词好句", path: "/booklearner", routePrefix: "booklearner" },
  { label: "我的生词本", path: "/wrong-words", routes: ["wrongWords"], countKey: "wrongWordCount" },
];

export function isSidebarNavItemActive(item, route) {
  if (item.routes?.includes(route.name)) return true;
  return Boolean(item.routePrefix && route.name.startsWith(item.routePrefix));
}
