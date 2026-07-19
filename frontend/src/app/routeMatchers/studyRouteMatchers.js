export const studyRouteMatchers = [
  {
    match: ([section]) => section === "growth",
    route: () => ({ name: "growth", params: {} }),
  },
  {
    match: ([section]) => section === "admin",
    route: () => ({ name: "admin", params: {} }),
  },
  {
    match: ([section, collection]) => section === "spb" && (!collection || collection === "team"),
    route: ([, collection]) => ({ name: "spb", params: { collection: collection || "individual" } }),
  },
  {
    match: ([section, day]) => section === "challenge-calendar" && day,
    route: ([, day]) => ({ name: "challengeDay", params: { day } }),
  },
  {
    match: ([section, id]) => section === "challenge" && id,
    route: ([, id]) => ({ name: "challenge", params: { id: Number(id) } }),
  },
  {
    match: ([section, id]) => section === "words" && id,
    route: ([, id]) => ({ name: "wordDetail", params: { id: Number(id) } }),
  },
];
