# Architecture summary — book-api (Rust / axum + rusqlite)

## Modules

| File | Role |
|------|------|
| `src/lib.rs` | Library crate: state, models, validation, handlers, router, unit tests (376 lines). |
| `src/main.rs` | Binary entry point: reads `PORT`/`BOOKS_DB` env, opens the DB, binds a `TcpListener`, serves the router (25 lines). |
| `tests/api.rs` | End-to-end HTTP integration tests driving the router against an in-memory SQLite DB (290 lines, 17 tests). |

## Key interfaces (`src/lib.rs`)

- `AppState { db: Arc<Mutex<Connection>> }` — shared state; `Arc`/`Mutex` wrap the synchronous `rusqlite::Connection` so it is `Clone` + `Sync` for axum's `State`.
- `Book` — `id, title, author, year: Option<i32>, isbn: Option<String>` (serde Serialize/Deserialize).
- `BookInput` — all-optional payload for POST/PUT; `validate()` trims and enforces required `title`/`author` and a `year` range (1000–2100).
- `ApiError { status, message }` — `IntoResponse` producing `{"error": ...}` JSON with the right status.
- `create_tables` / `open_db` — schema bootstrap.
- `router(state) -> Router` — wires `/`, `/health`, `/books` (POST+GET), `/books/{id}` (GET+PUT+DELETE).

## Request flow

HTTP → axum router → handler (`create_book`/`list_books`/`get_book`/`update_book`/`delete_book`) → lock `db` mutex → rusqlite query → map to `Book`/`ApiError` → JSON response with status code.

## Notes

- Persistence is real SQLite (`rusqlite` with the `bundled` feature); tests use `Connection::open_in_memory()`.
- Validation and status codes match the spec; PUT is full-replacement (omitted `year`/`isbn` are cleared) — a documented design choice.
