# Architecture Summary — book-api (rust / axum)

A single-crate Rust REST service. `run-summary` skill is not callable in this
environment, so this is a lightweight hand-written summary.

## Modules

- **`src/lib.rs`** (342 LOC) — the whole application: data types, DB setup,
  six route handlers, and the router builder. Also holds the only test module.
- **`src/main.rs`** (24 LOC) — binary entry point: builds `AppState`, wires the
  router via `create_app`, and serves on `127.0.0.1:3000`.

## Data types

- `Book` / `BookResponse` — persisted/serialised shape (id, title, author, year, isbn).
- `CreateBookRequest` — required fields for POST.
- `UpdateBookRequest` — all-optional fields for PUT.
- `AppState { db: SqlitePool }` — shared state; `AppState::new()` opens an
  in-memory SQLite pool and creates the `books` table.

## Routes (`create_app`)

| Method | Path | Handler |
|--------|------|---------|
| POST | `/books` | `create_book` |
| GET | `/books` | `get_books` |
| GET | `/books/:id` | `get_book` |
| PUT | `/books/:id` | `update_book` |
| DELETE | `/books/:id` | `delete_book` |
| GET | `/health` | `health_check` |

## Flow

`main` → `AppState::new()` (connect `sqlite::memory:`, `CREATE TABLE books`) →
`create_app(state)` → `axum::serve`. Handlers execute `sqlx::query` against the
pool and map results to JSON + status codes.

## Notable structural issues

- **Persistence is in-memory** and, worse, uses a *pool* over `sqlite::memory:` —
  each pooled connection owns a distinct database, so the table created at
  startup is not visible to other connections (see findings R7).
- **`get_books` reads no query string** — the `author` param is a bare
  `Option<String>` extractor, not `axum::extract::Query`, so `?author=` is never
  applied (findings R3).
- **Only one trivial test** exists, exercising a struct literal, not any route.
