# Run Summary: rest-api-crud (rust / codex / gpt-6-luna, rep3)

## Surface

A JSON REST API for a book collection, built with Rust + Axum 0.7 + SQLx/SQLite.
Single-file service (`src/main.rs`, 189 lines including tests) exposing CRUD over
`/books`, an `?author=` list filter, required-field validation, and a `/health`
check. Three handler-level integration tests run against an in-memory SQLite pool.

See [modules.md](modules.md) and [interfaces.md](interfaces.md).

## Architecture notes

- One module, `main.rs`. `AppState` holds a `SqlitePool`; handlers are free async
  functions wired in `app(state) -> Router`. A custom `ApiError` enum implements
  `IntoResponse` and `From<sqlx::Error>` for uniform JSON error bodies.
- Persistence: `database()` opens `sqlite:books.db?mode=rwc` (override via
  `DATABASE_URL`) and `CREATE TABLE IF NOT EXISTS books`. Tests use a 1-connection
  `sqlite::memory:` pool so the schema persists across queries.

## Key defect (see evaluation.md)

The router registers id routes as `/books/{id}`, which is **axum 0.8** path syntax.
The pinned dependency resolves to **axum 0.7.9 / matchit 0.7.3**, where `{id}` is a
*literal* path segment, not a parameter (0.7 uses `:id`). So `GET/PUT/DELETE
/books/<numeric-id>` never match and return 404 — three of the six CRUD endpoints
are non-functional, and 2 of 3 tests fail (test_coverage = 0.333).
