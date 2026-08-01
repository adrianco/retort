# Run Summary

**Surface:** A Rust REST API (axum + rusqlite/SQLite) for managing a book collection — full CRUD over `/books`, an `?author=` list filter, and a `/health` check.

- [modules.md](modules.md) — file-level structure
- [interfaces.md](interfaces.md) — HTTP routes and data schema

## Architecture at a glance

A single-crate axum service. `src/lib.rs` holds everything meaningful: `AppState` wraps a `Connection` behind `Arc<Mutex<>>`, `app()` builds the router, and six async handlers (`health`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`) implement the endpoints. `src/main.rs` is a thin binary that opens the DB (path from `DATABASE_URL`, default `books.db`), binds `127.0.0.1:3000`, and serves. Errors funnel through small helpers (`internal_error`, `not_found`, `validate`) that produce `(StatusCode, Json<ErrorResponse>)`. Tests live in a `#[cfg(test)]` module using `tower::ServiceExt::oneshot` against an in-memory SQLite instance.
