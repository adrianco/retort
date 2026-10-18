# Architecture Summary

`run-summary` skill not registered in this session; this is a concise hand-written
summary of the (small) codebase.

## Modules

| File | Role |
|------|------|
| `src/lib.rs` | The whole API: `Book` model, request validation, `rusqlite` persistence, axum router + 6 handlers, `ApiError` → HTTP mapping. Also hosts 4 validation unit tests. |
| `src/main.rs` | Thin binary: opens the SQLite file (`DATABASE_PATH`, default `books.db`), builds the router via `book_api::app`, serves on `PORT` (default 3000). |
| `tests/api.rs` | 9 integration tests driving the router with `tower::ServiceExt::oneshot` over an in-memory SQLite DB. |

## Interfaces

- `pub fn app(conn: Connection) -> rusqlite::Result<Router>` — builds the router and
  initialises the schema. The seam both `main` and the tests use.
- `pub fn init_schema(conn: &Connection)` — `CREATE TABLE IF NOT EXISTS books`.
- `pub struct Book { id, title, author, year: Option<i32>, isbn: Option<String> }` — the
  serialised response shape.
- `pub enum ApiError { BadRequest, Validation, NotFound, Internal }` — implements
  `IntoResponse`, rendering `{"error": "..."}` with the matching status.

## Flow

1. `main` opens a connection and calls `app`, which runs `init_schema` and registers routes:
   `/health`, `/books` (POST+GET), `/books/{id}` (GET+PUT+DELETE).
2. State is `Arc<Mutex<Connection>>`; every handler locks the single connection.
3. Create/update parse the raw `Bytes` body through `validate` (manual `serde_json` parse so
   malformed JSON → 400 and field errors → 422 are distinguished), then run parameterised SQL.
4. Reads go through `fetch_book`; absent rows map to `ApiError::NotFound` (404).

## Notes

- Single shared mutexed connection — correct for this scope, serialises all requests.
- Author filter uses `COLLATE NOCASE` for case-insensitive exact match.
- PUT is a full replacement (omitted `year`/`isbn` become null), documented in the README.
