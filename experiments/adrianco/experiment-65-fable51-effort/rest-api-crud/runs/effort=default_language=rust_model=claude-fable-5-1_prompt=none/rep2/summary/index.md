# Summary: effort=default·language=rust·model=claude-fable-5-1·prompt=none · rep 2

- **Shape:** Axum REST API with an embedded SQLite store (`rusqlite`, bundled engine).
- **Structure:** 6 source modules + 1 integration test file (10 tests total).
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter), library API exposed via `books_api`.
- **Notable:** Clean separation (handlers / db / models / error); typed error enum mapped to 400/404/409/500; validation extracted into `BookInput::validate`; `isbn UNIQUE` yields 409; lib/bin split enables `oneshot` router tests against `:memory:`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
