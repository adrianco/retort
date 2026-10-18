# Summary: effort=low language=rust model=claude-haiku-5-5 prompt=neutral · rep 3

- **Shape:** Axum 0.8 REST API over SQLite (`rusqlite`, bundled), with a clean HTTP/model/persistence split.
- **Structure:** 3 source modules (lib/book/main) + 1 integration test file; 15 test functions total (6 unit in `book.rs`, 9 integration in `tests/api.rs`).
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter); library entry `app(Connection) -> Router`.
- **Notable:** Idiomatic layered design — a custom `ApiError` enum with `IntoResponse`, all-fields-optional request type so validation collects every error, `Location` header on create, case-insensitive `COLLATE NOCASE` author filter, poisoned-lock recovery. Uses `422` for validation errors (rather than `400`) and adds beyond-spec ISBN/year validation.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
