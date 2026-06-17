export const listRouteMatchers = [
  {
    match: ([section, id]) => section === "lists" && id,
    route: ([, id]) => ({ name: "listDetail", params: { id: Number(id) } }),
  },
  {
    match: ([section]) => section === "lists",
    route: () => ({ name: "lists", params: {} }),
  },
  {
    match: ([section]) => section === "wrong-words",
    route: () => ({ name: "wrongWords", params: {} }),
  },
];
