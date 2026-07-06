# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | Binary entrypoint: opens SQLite, builds router, serves over TCP | `main()` |
| src/lib.rs | Crate root; wires routes to handlers | `build_router()` |
| src/handlers.rs | Axum async request handlers for all endpoints | `health`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `SharedDb` |
| src/models.rs | Data types + input validation | `Book`, `BookInput`, `BookQuery`, `BookInput::validate()` |
| src/db.rs | Connection open + schema init | `open()`, `init_schema()` |
| src/error.rs | Error enum mapped to HTTP responses | `AppError` |
| tests/api.rs | Integration tests over in-memory DB | 7 test functions |
