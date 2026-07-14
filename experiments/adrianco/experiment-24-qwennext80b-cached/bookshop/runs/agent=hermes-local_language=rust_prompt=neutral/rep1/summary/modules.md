# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Models, error type, all HTTP handlers, DB init; also a dead `main` copy | `Book`, `CreateBook`, `UpdateBook`, `BookError`, `init_pool()`, `health`, `get_books`, `get_book`, `create_book`, `update_book`, `delete_book` |
| src/main.rs | Binary entry point — builds the actix App and binds routes | `main()` |
| migrations/0001_init.sql | `books` table DDL (unused — schema is created inline in `init_pool`) | (SQL only) |
