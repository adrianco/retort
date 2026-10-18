# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | HTTP service: state, model, error type, 6 handlers, router, main, 3 tests | `app()`, `main()`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health`, `database()` |
| Cargo.toml | Crate manifest + deps (axum 0.7, sqlx 0.8, serde, tokio) | — |
| README.md | Setup/run/test instructions | — |

Tests: 3 `#[tokio::test]` functions in the `tests` module of `src/main.rs`.
