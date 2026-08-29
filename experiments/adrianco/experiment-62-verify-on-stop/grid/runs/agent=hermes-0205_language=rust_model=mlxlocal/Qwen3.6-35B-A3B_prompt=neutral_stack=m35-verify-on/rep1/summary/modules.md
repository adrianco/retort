# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | actix-web HTTP server, route handlers, server bootstrap, HTTP integration tests | `main`, `health_check`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| src/database.rs | SQLite CRUD layer over rusqlite + DB-layer unit tests | `create_book`, `list_books`, `get_book_by_id`, `update_book`, `delete_book` |
| src/models.rs | Serde data models, table DDL, connection factory | `Book`, `CreateBookRequest`, `UpdateBookRequest`, `TABLE_DEF`, `create_connection` |
