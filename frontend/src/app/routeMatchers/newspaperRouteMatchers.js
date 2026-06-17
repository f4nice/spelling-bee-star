export const newspaperRouteMatchers = [
  {
    match: ([section, sectionKey, articleIndex]) => section === "newspaper" && sectionKey && articleIndex,
    route: ([, section, index]) => ({ name: "newspaperArticle", params: { section, index: Number(index) } }),
  },
  {
    match: ([section]) => section === "newspaper",
    route: () => ({ name: "newspaper", params: {} }),
  },
];
