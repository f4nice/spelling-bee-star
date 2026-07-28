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
    match: ([section]) => section === "cat-world",
    route: () => ({ name: "catWorld", params: {} }),
  },
  {
    match: ([section]) => section === "essays",
    route: () => ({ name: "essays", params: {} }),
  },
  {
    match: ([section]) => section === "debate",
    route: () => ({ name: "debate", params: {} }),
  },
  {
    match: ([section]) => section === "spb",
    route: () => ({ name: "spb", params: { collection: "individual" } }),
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
