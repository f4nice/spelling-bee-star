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
    match: ([section, action, slug]) => section === "booklearner" && action === "science" && !slug,
    route: () => ({ name: "booklearnerScienceHome", params: {} }),
  },
  {
    match: ([section, action, slug]) => section === "booklearner" && action === "science" && slug,
    route: ([, , slug]) => ({ name: "booklearnerScience", params: { slug } }),
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
