# Architecture summary

> `run-summary` skill not invocable in this session — summary written inline.

Small Go REST service (`module bookapi`) using the chi router and `mattn/go-sqlite3`.

## Modules
- **main.go** — entry point; builds the router and serves on `:8080`.
- **router.go** — `NewRouter()` wires routes; `Book` struct + 6 HTTP handlers
  (health, create, list, get, update, delete). JSON in/out, validation, status codes.
- **db.go** — `initDB()`/`getDB()` open a SQLite DB (path from `BOOKAPI_DB` env or
  `books.db`), create the `books` table, and cache a package-global `*sql.DB` singleton.
- **router_test.go** — `TestHealth`, `TestCRUD` against an in-memory shared-cache DB.

## Flow
HTTP request → chi router → handler → `getDB()` → SQLite query → JSON response.

## Notes
- `getDB()` returns the cached global `db`; `initDB()` short-circuits when `db != nil`,
  so a second `setupTestDB()` does not re-open even if `BOOKAPI_DB` changes.
- No README.md present despite the agent's stdout claiming one was created.
