export const studyRouteMatchers = [
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
