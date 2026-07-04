export const studyRouteMatchers = [
  {
    match: ([section]) => section === "growth",
    route: () => ({ name: "growth", params: {} }),
  },
  {
    match: ([section]) => section === "spb",
    route: () => ({ name: "spb", params: {} }),
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
