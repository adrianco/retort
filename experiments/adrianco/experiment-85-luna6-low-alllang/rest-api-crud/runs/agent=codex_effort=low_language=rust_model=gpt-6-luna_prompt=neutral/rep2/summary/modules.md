# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | Axum HTTP server, SQLite-backed book CRUD, route handlers, and inline tests | `main`, `app()`, `build_app()`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |

Single-file project. `Cargo.toml` declares dependencies (axum 0.8, rusqlite 0.32 bundled, serde, serde_json, tokio; dev: tower). Tests live in a `#[cfg(test)] mod tests` block at the bottom of `src/main.rs` (4 test functions).
