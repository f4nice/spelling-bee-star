import { booklearnerRouteMatchers } from "./booklearnerRouteMatchers.js";
import { importRouteMatchers } from "./routeMatchers/importRouteMatchers.js";
import { listRouteMatchers } from "./routeMatchers/listRouteMatchers.js";
import { newspaperRouteMatchers } from "./routeMatchers/newspaperRouteMatchers.js";
import { studyRouteMatchers } from "./routeMatchers/studyRouteMatchers.js";

export const routeMatchers = [
  ...listRouteMatchers,
  ...studyRouteMatchers,
  ...importRouteMatchers,
  ...newspaperRouteMatchers,
  ...booklearnerRouteMatchers,
];

export const homeRoute = { name: "home", params: {} };
