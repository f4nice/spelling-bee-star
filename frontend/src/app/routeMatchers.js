import { booklearnerRouteMatchers } from "./booklearnerRouteMatchers.js";

export const routeMatchers = [
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
  {
    match: ([section, preview, id]) => section === "upload" && preview === "preview" && id,
    route: ([, , id]) => ({ name: "preview", params: { id } }),
  },
  {
    match: ([section]) => section === "upload",
    route: () => ({ name: "upload", params: {} }),
  },
  {
    match: ([section, sectionKey, articleIndex]) => section === "newspaper" && sectionKey && articleIndex,
    route: ([, section, index]) => ({ name: "newspaperArticle", params: { section, index: Number(index) } }),
  },
  {
    match: ([section]) => section === "newspaper",
    route: () => ({ name: "newspaper", params: {} }),
  },
  ...booklearnerRouteMatchers,
];

export const homeRoute = { name: "home", params: {} };
