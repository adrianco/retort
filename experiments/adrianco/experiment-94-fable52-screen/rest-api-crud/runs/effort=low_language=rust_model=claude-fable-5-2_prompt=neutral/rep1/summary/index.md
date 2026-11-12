# Architecture Summary: books-api (Rust / axum / rusqlite)

## Modules
- **src/lib.rs** (241 LOC) — the whole service: `Db` (SQLite handle behind
  `Arc<Mutex<Connection>>`), domain types (`Book`, `BookInput`, `ValidBook`),
  `ApiError` with `IntoResponse`, validation, row mapping, six handlers, and the
  `app(db) -> Router` builder.
- **src/main.rs** (12 LOC) — binary entrypoint: reads `DATABASE_PATH`/`PORT`,
  opens the DB, serves the router via `axum::serve` on a tokio runtime.
- **tests/api.rs** (158 LOC) — 8 integration tests driving the router in-process
  with `tower::ServiceExt::oneshot` against an `:memory:` DB.

## Interfaces (routes)
`GET /health`, `POST /books`, `GET /books` (+ `?author=`),
`GET|PUT|DELETE /books/{id}` — wired in `app()` (lib.rs:235-241).

## Flow
Request → axum extractor (`State<Db>`, `Query`/`Path`, `Json` body as a
`Result` to capture rejections) → `validate()` for writes → `rusqlite`
prepared statement under the mutex → `Book`/status serialized to JSON.
Errors funnel through `ApiError::into_response` producing `{"error": ...}`
bodies with 400/404/422/500 codes.

## Notes
- Clean separation of validation from persistence; parameterized SQL throughout
  (no string interpolation of user values — `?author=` uses a bound param).
- Handler signatures take extractor `Result`s so malformed JSON / non-numeric
  IDs become 400s with JSON bodies rather than framework plain-text rejections.
