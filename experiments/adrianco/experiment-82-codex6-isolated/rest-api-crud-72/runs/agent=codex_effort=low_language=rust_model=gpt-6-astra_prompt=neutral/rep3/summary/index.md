# Architecture Summary — book-collection (Rust / Axum / SQLite)

A single-crate Axum REST service for a book collection, backed by SQLite via
`rusqlite` (bundled). ~488 lines of Rust across three files.

## Modules

| File | Role |
|------|------|
| `lib.rs` (244) | Whole application: `Database` wrapper, `Book`/`BookInput` models, `ApiError`, the `app()` router, and all six handlers. |
| `main.rs` (16) | Binary entry point: reads `DATABASE_PATH`/`BIND_ADDRESS`, opens the DB, serves `app()` with graceful Ctrl-C shutdown. |
| `tests.rs` (228) | 5 `#[tokio::test]` integration tests driving the router via `tower::ServiceExt::oneshot`. |

## Key interfaces

- `Database(Arc<Mutex<Connection>>)` — a single shared connection serialized by a
  `Mutex`; `run()` offloads blocking SQLite work onto `tokio::task::spawn_blocking`.
  Schema created on `open()` with `NOT NULL` + `CHECK(length(trim(...)) > 0)` on
  title/author.
- `app(Database) -> Router` — routes: `GET /health`, `GET|POST /books`,
  `GET|PUT|DELETE /books/{id}`, plus a 404 fallback and a 405
  `method_not_allowed_fallback`.
- `ApiError(StatusCode, String)` — uniform `{"error": ...}` JSON error body;
  `From<rusqlite::Error>` maps DB errors to 500 (logging the detail to stderr).

## Request flow

1. Extractors return `Result<_, Rejection>`; helpers `input()`/`id()` convert
   rejections to 400 and validate (trim + non-blank for title/author, positive
   integer for id).
2. Handler builds a closure and calls `db.run()`, which locks the connection on a
   blocking worker and runs the SQL.
3. Success serializes to JSON with the right status (201 + Location on create,
   200 on read/update, 204 on delete); `get_book` maps a missing row to 404.

## Notable properties

- Parameterized SQL throughout (tested against an injection-like author filter).
- Author filter is a single `WHERE (?1 IS NULL OR author=?1)` — exact,
  case-sensitive.
- PUT is a full replace: omitted optional fields (`year`, `isbn`) become null.
- Persistence verified by a test that reopens a file-backed DB.
