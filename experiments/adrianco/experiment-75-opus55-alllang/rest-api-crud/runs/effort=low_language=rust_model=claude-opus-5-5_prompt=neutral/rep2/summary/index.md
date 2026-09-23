# Architecture Summary: books-api (Rust)

> Written inline by `evaluate-run`; the `run-summary` skill was not available in
> this session. The codebase is small (3 source files, 290 LOC) so this is complete.

## Stack

- **Language/edition:** Rust 2021
- **Web framework:** Axum 0.8 (Tokio async runtime, full features)
- **Persistence:** rusqlite 0.32 with the `bundled` SQLite feature
- **Serialization:** serde / serde_json
- **Test deps:** tower (`util`), http-body-util — for `oneshot` in-process request testing

## Modules

| File | Role |
|------|------|
| `src/lib.rs` | Entire application: models, DB open/schema, router, handlers, error type |
| `src/main.rs` | Binary entrypoint: reads `DATABASE_PATH`/`BIND_ADDR`, opens DB, serves the router |
| `tests/api.rs` | Integration tests driving the router in-process against `:memory:` |

## Interfaces

- **`Book`** — persisted model (`id`, `title`, `author`, `year: Option<i32>`, `isbn: Option<String>`).
- **`BookInput`** — request body (all fields `Option`; validated in `validate`).
- **`ApiError`** — `NotFound` (404) / `Validation(Vec<String>)` (400) / `Internal(String)` (500),
  each with an `IntoResponse` mapping to a JSON body. `From<rusqlite::Error>` folds DB errors to 500.
- **`Db = Arc<Mutex<Connection>>`** — a single SQLite connection guarded by a mutex, shared as Axum state.

## Routes (`app()`)

- `GET /health` → `{"status":"ok"}`
- `POST /books` → 201 + created book (validated)
- `GET /books` (`?author=` exact-match filter) → 200 + list
- `GET /books/{id}` → 200 or 404
- `PUT /books/{id}` → 200 or 404 (full replace, re-validated)
- `DELETE /books/{id}` → 204 or 404

## Flow

`main` resolves config from env → `open_db` opens/creates the SQLite file and ensures the
`books` table → `app(db)` builds the router with the connection as shared state → each handler
locks the mutex, runs a parameterized query, and maps results/errors through `ApiError`.
Validation trims `title`/`author` and rejects empties with a 400 listing each missing field.
