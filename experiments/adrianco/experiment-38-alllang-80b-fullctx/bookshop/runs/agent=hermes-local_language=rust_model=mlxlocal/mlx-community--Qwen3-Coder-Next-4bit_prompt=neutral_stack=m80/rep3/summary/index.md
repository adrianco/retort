# Run Summary — book-api (Rust / actix-web / sqlx-sqlite)

## Surface

A REST API for a book collection: CRUD over `/books`, an `?author=` list filter,
and a `/health` check. Persistence is SQLite via `sqlx`. Built as a lib + binary
(`book-api`) using actix-web 4.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `src/lib.rs` | Data models, error type, validation attrs | `Book`, `CreateBookRequest`, `UpdateBookRequest`, `HealthResponse`, `AppError` |
| `src/repository.rs` | SQLite CRUD + table bootstrap + 5 unit tests | `BookRepository`, `new()`, `create_book`, `get_books`, `get_book_by_id`, `update_book`, `delete_book` |
| `src/api.rs` | actix handlers | `health`, `get_books`, `get_book`, `create_book`, `update_book`, `delete_book` |
| `src/main.rs` | Server bootstrap + routing table | `main()` |

## Flow

`main` → `BookRepository::new("sqlite://data.db")` (creates `books` table) →
`HttpServer` with `web::Data<BookRepository>` shared → routes dispatch to `api.rs`
handlers → repository executes parameterized `sqlx` queries → results serialized to
JSON via `serde`. Errors flow through `AppError` implementing `actix_web::ResponseError`.

## Notable

- `AppError` maps Database→500, Validation→400, NotFound→404.
- DELETE correctly returns 404 (checks `rows_affected`); GET-by-id and PUT rely on
  `fetch_one`, so a missing row surfaces as `sqlx::Error::RowNotFound`→`Database`→**500**,
  not 404. See findings.
- Tests exercise the repository layer only (no handler/HTTP-status coverage).
