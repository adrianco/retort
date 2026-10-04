# Architecture Summary — books-api (Rust / axum / rusqlite)

Small, cleanly-layered REST service. 569 LOC across 4 Rust files.

## Modules

| File | Role |
|------|------|
| `src/main.rs` | Binary entrypoint. Reads `PORT` / `DATABASE_PATH` env, opens the DB, binds a `TcpListener`, serves the router with graceful `ctrl_c` shutdown. |
| `src/lib.rs` | Library crate root (`books_api`). Owns the `Router` (`app`), all HTTP handlers, request parsing/validation (`BookInput::validate`), and the `ApiError` → JSON response mapping. |
| `src/db.rs` | SQLite data layer: schema init (`open` / `open_in_memory`), `Book`/`BookFields` types, and CRUD query functions (`insert`, `list`, `get`, `update`, `delete`). |
| `tests/api.rs` | 9 integration tests driving the in-process router against an in-memory SQLite DB via `tower::ServiceExt::oneshot`. |

## Interfaces / flow

- **State**: `Arc<Mutex<Connection>>`. A single SQLite connection guarded by a mutex; DB calls run on `spawn_blocking` so SQLite I/O never stalls the async runtime. Poisoned-lock recovery via `into_inner()`.
- **Routing**: `/health`, `/books` (GET list + POST create), `/books/{id}` (GET/PUT/DELETE), plus a JSON 404 fallback.
- **Validation**: all request fields deserialize as `Option`, then `validate()` collects field errors (title/author required + non-blank after trim, year 0–9999) into a `400 {"error","details":[…]}`.
- **Errors**: `ApiError` enum → structured JSON with correct status (400/404/500). `rusqlite::Error` logged to stderr and mapped to 500.
- **Persistence**: real SQLite table `books` with an author index (`COLLATE NOCASE`); author filter is exact, case-insensitive.

## Notable qualities

- Clear separation of transport (lib.rs) from storage (db.rs); binary is a thin shell.
- `201 Created` with a `Location` header; `204 No Content` on delete; idempotent delete returns 404 second time.
- Tests cover happy path, optional-field omission, validation rejection, malformed JSON, author filter, update-replace semantics, delete, and invalid/unknown ids.
