# Summary: language=rust · model=sonnet-5 · prompt=tdd · rep 1

- **Shape:** Rust REST API with axum 0.7 + rusqlite (bundled SQLite), single mutex-guarded connection.
- **Structure:** 5 source modules, 2 test files (13 integration tests).
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter), 1 SQLite table.
- **Notable:** Clean layered separation (models / db / handlers / router). `PRAGMA journal_mode=MEMORY` chosen to avoid sandbox journal-file write failures. Tests run against an in-memory DB via `test_support::test_app()`. Concurrency is serialized through a single `Arc<Mutex<Connection>>` (no pool).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
