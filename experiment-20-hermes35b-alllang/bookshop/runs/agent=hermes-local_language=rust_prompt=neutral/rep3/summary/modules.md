# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | Actix-web HTTP server, SQLite data layer, route handlers, and unit tests — single-file app | `main()`, `Db`, `Book`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health` |

The entire project is one source file: models, DB access layer (`Db`), request handlers, the `#[actix_web::main]` entry point, and a `#[cfg(test)]` module with 10 tests.
