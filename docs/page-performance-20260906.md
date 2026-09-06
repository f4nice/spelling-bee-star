# Page loading performance — 2026-09-06

## Changes

- Home/list/SPB cards use grouped counts, one cover per list, and batched challenge-history queries instead of loading every full word in every list.
- Covers now consistently prefer the most recently inserted illustrated word (previously a random illustrated word).
- Challenge progress creation and round rollover still use the original handler. Historical attempts with no list ID retain their legacy behavior.
- Pending wrong-word totals use four bulk queries, preserving date-based correction and deduplication rules.
- Serialized account-independent shell statistics are cached for 10 seconds, keyed by database engine and date. User identity and permissions are always resolved per request. Successful mutations invalidate the cache; play-time heartbeats do not, because they do not change these statistics.
- Gzip compresses JS/CSS/SVG/JSON static assets and Vue GET API responses. Audio, auth HTML and range requests bypass it.
- Content-hashed Vue chunks are immutable; non-hashed entry JS and CSS still revalidate so releases remain discoverable.

## Production measurements

These are application-function timings on the same server/data, not full browser page-load times. Auditing used a read-only database transaction and blocked SQL writes. Two measurements were made for each path.

| Read path | Before | After | SQL queries before → after |
| --- | ---: | ---: | ---: |
| Home API | 0.73–0.74 s | 0.118–0.123 s | 374 → 20 |
| Lists API | 0.77 s | 0.098–0.100 s | 438 → 7 |
| SPB API | 0.69–0.71 s | 0.085–0.092 s | 264 → 82 |
| Shell, cold statistics | 0.32–0.36 s | 0.141 s | 582 → 17 |
| Shell, statistics cache hit | 0.32–0.36 s | <0.001 s | 582 → 0 |

Authenticated requests additionally resolve the current account; that work is deliberately not cached.

The Cat World game chunk transfers about 408 KB with gzip instead of 1.76 MB uncompressed. The public endpoint returned `Content-Encoding: gzip` and `Vary: Accept-Encoding`. Range checks returned 206 with exactly the requested 100 bytes, without gzip.

## Verification

- 81 production lists: old/new challenge state and word counts matched.
- 552 pending wrong words: old/new totals matched.
- 38 tests passed across page performance, SPB refresh, word completion, web dictionary, and Cat World reward/play-time suites.
- Browser smoke checks passed for home, lists, SPB, essays, word detail and Booklearner. These are functional checks; first-resource/browser timing still varies, so the table does not claim end-to-end browser latency.
- No schema migration, data rewriting, or frontend rebuild was required. Concurrent Cat World feature changes were preserved.

## Operations

Only `app/main.py` and the new `app/services/page_performance.py` were deployed. The pre-change server main file was backed up in the existing staging `code-backups/performance-before-20260906.tar.gz` archive. Restore only that backed-up file and restart the application if an immediate rollback is required; preserve any later changes first. The unused helper module can remain in place safely.
