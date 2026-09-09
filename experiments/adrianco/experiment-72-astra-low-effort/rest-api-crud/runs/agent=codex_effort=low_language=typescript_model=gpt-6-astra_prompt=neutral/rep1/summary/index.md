# Architecture summary

Small, clean layered TypeScript/Express 5 service (308 LOC across 4 source files).

- **`store.ts`** — `BookStore` wraps Node's built-in `node:sqlite` `DatabaseSync`.
  Schema with `NOT NULL` + `CHECK(length(trim(...)) > 0)` on title/author. CRUD via
  prepared, parameterized statements (SQL-injection safe). `:memory:` default,
  file-backed via constructor path. `healthy()` probes with `SELECT 1`.
- **`app.ts`** — `createApp(store)` builds the Express app. `validateBook` enforces
  required non-blank `title`/`author`, optional safe-integer `year`, optional
  non-blank `isbn`. Routes: `/health`, `POST/GET/GET:id/PUT/DELETE /books`. `app.param('id')`
  rejects non-positive/non-safe integer ids with 400. Centralized error handler maps
  BadRequest→400, parse-failure→400, too-large→413, 415→415, else 500.
- **`server.ts`** — entry point: validates `PORT`, opens file-backed store (`DB_PATH`),
  graceful shutdown on SIGINT/SIGTERM.
- **`app.test.ts`** — 6 `node:test` tests over in-memory HTTP (no TCP bind) covering CRUD
  round-trip, author filter + SQL-injection-as-data, validation rejection, 404/400 id
  handling + health + unknown route, malformed/oversized JSON, and SQLite persistence
  across reopen.

Dependency direction: `server → app → store`. No web framework beyond Express; no ORM.
