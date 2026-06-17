export const importRouteMatchers = [
  {
    match: ([section, preview, id]) => section === "upload" && preview === "preview" && id,
    route: ([, , id]) => ({ name: "preview", params: { id } }),
  },
  {
    match: ([section]) => section === "upload",
    route: () => ({ name: "upload", params: {} }),
  },
];
