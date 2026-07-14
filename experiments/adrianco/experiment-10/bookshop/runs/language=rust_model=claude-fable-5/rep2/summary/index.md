# Architecture Summary: books-api (Rust / Axum)

## Modules

| Module | Path | Purpose |
|--------|------|---------|
| lib | `src/lib.rs` | Router, handlers, validation, DB schema, error types |
| main | `src/main.rs` | Server entry point — binds TCP listener, opens SQLite |
| tests | `tests/api.rs` | Integration tests using in-memory SQLite + tower oneshot |

## Key Types

- `Book` — serializable row struct (id, title, author, year, isbn)
- `BookInput` — deserialized request body (all fields optional for validation)
- `ListParams` — query params for GET /books (?author=)
- `ApiError` — enum mapping validation/not-found/internal errors to HTTP status + JSON
- `Db` — `Arc<Mutex<Connection>>` shared state

## Data Flow

1. `main.rs` opens a SQLite file (or `DATABASE_PATH` env), calls `app(conn)` to build the router.
2. `app()` calls `init_db()` (CREATE TABLE IF NOT EXISTS), wraps connection in `Arc<Mutex<>>`, returns an Axum `Router` with state.
3. Each handler locks the mutex, runs a parameterized query, maps rows to `Book`, returns JSON.
4. `validate()` gates POST and PUT — rejects empty/whitespace title or author with 400.

## Dependencies (7 total)

**Runtime (5):** axum 0.8, tokio 1, serde 1, serde_json 1, rusqlite 0.32 (bundled SQLite)
**Dev (2):** tower 0.5, http-body-util 0.1

## Test Strategy

Integration tests via `tower::ServiceExt::oneshot` — no network, no running server. Each test creates a fresh in-memory SQLite DB via `test_app()`. 7 tests cover all CRUD operations, validation, filtering, and 404 handling.
