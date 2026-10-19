# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Book API library: types, SQLite access, axum handlers, router | `Book`, `AppState`, `init_db()`, `router()`, `validate_required()`, handlers (`create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health`, `about`) |
| src/main.rs | Binary entry point: opens SQLite, builds router, starts axum server | `main()` |
| tests/integration.rs | Full HTTP-stack integration tests over in-memory SQLite | 19 `#[tokio::test]` functions + helpers |
