# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `src/main.rs` | Actix-Web server + 6 route handlers | `main()`, `health`, `create_book`, `get_books`, `get_book`, `update_book`, `delete_book` |
| `src/database.rs` | SQLite schema + CRUD via sqlx | `Database::new`, `create_book`, `get_book(s)`, `update_book`, `delete_book` |
| `src/models.rs` | Data types + conversions | `Book`, `BookInput`, `HealthResponse` |
| `src/lib.rs` | Placeholder lib w/ the only `#[test]` | `add()`, `it_works` (trivial `2+2` test) |
| `book_api/src/main.rs` | Dead stub crate ("Hello, world!") | `main()` |
| `test_api.sh` | Manual curl smoke script (not a cargo test) | — |
| `Cargo.toml` | actix-web 4, serde, serde_json, sqlx 0.8, tokio | — |
