export const booklearnerRouteMatchers = [
  {
    match: ([section, action]) => section === "booklearner" && action === "upload",
    route: () => ({ name: "booklearnerUpload", params: {} }),
  },
  {
    match: ([section, action]) => section === "booklearner" && action === "quotes",
    route: () => ({ name: "booklearnerQuotes", params: {} }),
  },
  {
    match: ([section, detail, id]) => section === "booklearner" && detail === "detail" && id,
    route: ([, , id]) => ({ name: "booklearnerDetail", params: { id: Number(id) } }),
  },
  {
    match: ([section]) => section === "booklearner",
    route: () => ({ name: "booklearner", params: {} }),
  },
];
