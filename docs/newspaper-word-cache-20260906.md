# Newspaper and word detail caching — 2026-09-06

## Behavior

- Newspaper snapshots persist in `speakeasy_cache` for 45 minutes. An expired snapshot is returned immediately while a background thread refreshes it on demand. A previous day's/legacy snapshot is reused during rollover. This is request-driven, not a scheduled job.
- The page includes an update button, an update timestamp, and background-refresh feedback. The button starts a non-blocking refresh; concurrent refreshes are coalesced and starts are limited to once per 30 seconds per process.
- Upstream failures retain the last successful snapshot. Partial failures retain the previous affected section and label it as cached content.
- Source sections are fetched with at most three workers. Bodies already fetched for summaries are retained server-side and cached by article URL for six hours, avoiding another crawl of the whole section when reading one article.
- List API responses omit full bodies. The browser caches list responses for five minutes and article responses for ten minutes, invalidates them on manual refresh, and does not reuse them across a local calendar-day boundary. Pending/failed refresh responses are not cached in the browser.
- Article links include their source URL so a list refresh cannot silently change which article an existing card opens. Only HTTPS article URLs on the allowed China Daily hosts and article-path format are accepted.
- Word details have a 15-second bounded server cache keyed by database, word ID, word revision, edit mode and navigation context. Each read still verifies that the word exists. Successful mutations invalidate this cache; background changes to the word revision also force a miss. Authentication is checked outside the cache on every request.
- Word audio version parameters now remain stable until the word changes, allowing the existing browser audio cache to work.

## Verification

- 51 Python tests and 59 JavaScript tests passed; frontend production builds passed.
- Live newspaper snapshot: six sections, 25 articles. Manual refresh, article navigation, direct article load and cache reuse verified in the browser.
- Word 20101 (`fomentation`, list 204) displayed correctly after refresh.
- Read-only server timings: newspaper list 0.8–1.5 ms, cached article about 1 ms; word detail 18.2 ms on cache miss, 0.6 ms on hit (seven queries down to one). These are backend function timings, not end-to-end browser load times.
- The user's earlier failed word page displayed an Nginx 404, not the application's missing-word response. Reloading restored it. Separate public login requests also showed intermittent network delay despite a fast loopback response. Application/data caches do not guarantee availability during an ingress interruption or a service restart.

## Deployment

Backend changes were applied as a reviewed minimal patch. The production frontend was built from a fresh production source snapshot with only the targeted changes applied, preserving unrelated production fixes. Repository build artifacts were regenerated separately from repository source. Old hashed frontend files were retained on the production server.

Pre-change files were backed up under the existing staging `code-backups/newspaper-word-cache-before-20260906.tar.gz`. Restore only the affected files after checking for later changes if rollback is necessary. Cache records can remain safely; no schema changes or learning-data migration were needed.
