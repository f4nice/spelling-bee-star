import { homeRoute, routeMatchers } from "./routeMatchers.js";

function routeQuery(search = window.location.search) {
  return Object.fromEntries(new URLSearchParams(search).entries());
}

export function parseRoute(pathname = window.location.pathname, search = window.location.search) {
  const path = pathname.replace(/\/$/, "").replace(/^\//, "");
  const parts = path ? path.split("/") : [];
  const query = routeQuery(search);
  if (!parts.length) return { ...homeRoute, query };
  const matchedRoute = routeMatchers.find((matcher) => matcher.match(parts));
  const route = matchedRoute ? matchedRoute.route(parts) : homeRoute;
  return { ...route, query };
}
