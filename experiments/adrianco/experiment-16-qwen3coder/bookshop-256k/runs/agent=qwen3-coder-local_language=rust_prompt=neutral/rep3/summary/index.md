# Architecture Summary — book-api (rust / qwen3-coder-local / neutral, rep3)

## Overview

A single-crate Rust REST service for a book collection, built on **warp 0.3** + **tokio**.
The entire production application lives in one file, `src/main.rs` (217 LOC). It exposes
six routes and one health check, all wired in `main()` and combined with `.or(...)`.

## Modules & structure

| Path | Role | Notes |
|------|------|-------|
| `src/main.rs` | Whole production service: models, storage, handlers, router, `main()` | Only file compiled into the binary |
| `src/main_test.rs` | Substantive-looking sqlx/SQLite integration tests | **Dead code** — not declared as a module anywhere, so never compiled or run |
| `tests/integration_tests.rs` | Integration-test binary | 2 trivial tests (`assert_eq!(true,true)` + a JSON-shape check) |
| `tests/api_tests.rs` | Integration-test binary | 1 trivial test (`assert_eq!(true,true)`) |

## Data model

`Book { id: String, title, author, year: i32, isbn }` — a single flat struct with
`serde` derive. There is no separate create/DTO type, so `POST /books` requires the
client to supply the `id`.

## Storage

`static mut BOOKS: Option<Vec<Book>>` — a **process-global mutable Vec** accessed through
`unsafe` blocks in every handler. Despite `Cargo.toml` declaring `sqlx` (sqlite) and
`uuid`, **`main.rs` imports neither** — there is no database and no persistence.

## Interfaces (routes)

- `GET /books` (+ `?author=` filter) → `get_books`
- `POST /books` → `create_book` (validates non-empty title/author, 201)
- `GET /books/{id}` → `get_book_by_id` (404 via custom rejection)
- `PUT /books/{id}` → `update_book`
- `DELETE /books/{id}` → `delete_book` (204 No Content)
- `GET /health` → `health_check` (`{"status":"OK"}`)
- `handle_rejection` maps `BookError::{BookNotFound,InvalidInput}` → 404/400 JSON.

## Control flow

`main()` builds each route filter, `.or`s them into `routes`, attaches `.recover(handle_rejection)`,
and serves on `127.0.0.1:3030`. Handlers read/mutate the global `BOOKS` under `unsafe`.

## Key architectural concerns

1. **No database** — storage is an in-memory global, contradicting the SQLite requirement (R7).
2. **`unsafe static mut`** shared across warp's multi-threaded runtime → data races / UB.
3. **Test/impl divergence** — the real tests never compile; the running tests exercise
   none of `main.rs`'s handlers.
