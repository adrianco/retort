# Summary: language=rust_model=sonnet-5_prompt=none · rep 1

- **Shape:** Axum REST API with SQLite (rusqlite bundled), shared `Arc<Mutex<Connection>>` state.
- **Structure:** 6 source modules + 1 integration test file (7 tests).
- **Interfaces:** 6 HTTP routes (5 CRUD + health), 1 exported `build_router`, 1 `books` table.
- **Notable:** Clean idiomatic layering (handlers / models / db / error split); centralized `AppError` → HTTP mapping; validation trims whitespace and distinguishes which field is missing. Synchronous DB behind a global `Mutex` serializes all requests (fine for the task, not for concurrency).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
