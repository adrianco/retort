# Run Summary — bookshop-128k · rust · qwen3-coder-local · rep3

**Shape:** single Actix-Web REST service backed by SQLite (via sqlx), plus a stray
placeholder crate under `book_api/`.

**Surface:** A REST API for a book collection — CRUD over `/books`, an `?author=`
list filter, and a `/health` check. Data persisted to a SQLite file (`books.db`).

See `modules.md` for the module map.

## Control flow

`src/main.rs` wires an `actix_web::HttpServer` with six routes (`health`,
`create_book`, `get_books`, `get_book`, `update_book`, `delete_book`). A
`SqlitePool` is built at startup and stored as `web::Data`, but **each handler
ignores it** and instead opens a fresh `Database::new("sqlite://books.db")`
connection per request. `src/database.rs` owns the schema (`CREATE TABLE IF NOT
EXISTS books`) and the CRUD SQL. `src/models.rs` defines `Book`, `BookInput`,
`HealthResponse` and the row/input conversions.

The `book_api/` subdirectory is a separate, empty stub crate
(`fn main(){ println!("Hello, world!"); }`, no dependencies) — dead scaffolding
unrelated to the working service.
