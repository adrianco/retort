# Run Summary — book-api (rust / actix-web / hermes-local / ATDD)

## Surface

A single-crate REST API for a book collection: CRUD over `/books`, an
`?author=` list filter, and a `/health` check. Built on actix-web 4 with an
in-process store. Intended (per TASK.md) to persist to SQLite/embedded DB.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | Everything: models, app state, all route handlers, `main()` server bootstrap, and the `#[cfg(test)]` acceptance suite | `main()`, `health_check`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |

## Interfaces

- `Book { id: Option<u32>, title, author, year: Option<u32>, isbn: Option<String> }` — serialized to/from JSON.
- `BookInput { title, author, year?, isbn? }` — request body for POST/PUT.
- `AppState { books: Mutex<Vec<Book>> }` — the entire persistence layer (in-memory).
- HTTP routes wired in `main()` (src/main.rs:64-69).

## Control flow

`main()` seeds the store with 2 hard-coded books, wraps a `Logger`, binds
`127.0.0.1:8080`, and serves. Each handler locks the shared `Mutex<Vec<Book>>`,
mutates/reads the vector, and returns JSON. IDs are assigned as `max(id)+1`.
Validation (non-empty title/author) is duplicated inline in `create_book` and
`update_book`.

## Notable

- No database: `fs::create_dir_all("data")` creates an unused `data/` directory;
  persistence is purely the in-memory `Vec`, lost on restart.
- Test module contains 8 `#[actix_web::test]` functions but only
  `test_health_check` exercises anything; the other 7 are `assert!(true)` stubs.
