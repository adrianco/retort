# Architecture Summary

Single-crate Axum + SQLite (sqlx) service, all in `src/main.rs` (319 lines incl. tests).

## Modules / structure

- **Data types**: `Book` (sqlx `FromRow`), `BookInput` (deserialize), `ListQuery` (`?author=`), `ErrorBody`.
- **Error handling**: `ApiError(StatusCode, &'static str)` implementing `IntoResponse`, rendered as `{"error": ...}` JSON. Handlers return `Result<_, ApiError>`.
- **Handlers**: `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health`. Shared `get_book_row` helper fetches-or-404.
- **Routing**: `app(db)` wires `/health`, `/books` (POST+GET), `/books/:id` (GET+PUT+DELETE), with `AppState { db }`.
- **Persistence**: `database(url)` opens a `SqlitePool` and creates the `books` table (`CREATE TABLE IF NOT EXISTS`). `main` reads `DATABASE_URL`/`BIND_ADDR` env vars.

## Flow

Request → extractor (`State`/`Path`/`Query`/`Json`) → `validate()` on write paths → parameterized sqlx query → JSON response with status code (201/200/204/400/404/500).

## Tests

`#[cfg(test)]` module with 4 `#[tokio::test]` integration tests driving the router via `tower::ServiceExt::oneshot` against an in-memory SQLite DB: health, create+retrieve, validation+404, and filter+update+delete.

_(run-summary skill not registered as a Skill-tool invocable in this session; summary authored inline.)_
