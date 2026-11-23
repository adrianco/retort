# Architecture summary

Single-file Axum (0.8) service in `main.rs` (208 LOC) with route tests in `tests.rs` (93 LOC).

- **State**: `Db(Arc<Mutex<Connection>>)` — a bundled rusqlite SQLite connection shared across handlers; blocking DB work runs on `spawn_blocking`.
- **Routes** (`app`): `GET /health`, `GET/POST /books`, `GET/PUT/DELETE /books/{id}`, plus a 404 fallback and a 405 method-not-allowed fallback.
- **Model**: `Fields{title,author,year?,isbn?}` flattened into `Book{id, ..fields}` for serialization.
- **Validation** (`validate`): trims title/author, rejects blank with 422; malformed JSON surfaces the JsonRejection status (400).
- **Errors**: unified `Error(StatusCode, String)` → JSON `{"error": ...}`; DB errors mapped to 500 with a generic message, missing rows to 404.
- **Config**: `BOOKS_DB` / `BOOKS_ADDR` env overrides; table created idempotently at startup.

(run-summary skill not invoked — not registered in this harness; architecture captured inline.)
