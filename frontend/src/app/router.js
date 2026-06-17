import { homeRoute, routeMatchers } from "./routeMatchers.js";

export function parseRoute(pathname = window.location.pathname) {
  const path = pathname.replace(/\/$/, "").replace(/^\//, "");
  const parts = path ? path.split("/") : [];
  if (!parts.length) return homeRoute;
  const matchedRoute = routeMatchers.find((matcher) => matcher.match(parts));
  return matchedRoute ? matchedRoute.route(parts) : homeRoute;
}
