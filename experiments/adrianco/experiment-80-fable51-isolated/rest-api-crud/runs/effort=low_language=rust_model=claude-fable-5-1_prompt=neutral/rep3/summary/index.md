# Summary: effort=low_language=rust_model=claude-fable-5-1_prompt=neutral · rep 3

- **Shape:** Rust axum 0.8 REST API with SQLite persistence (rusqlite, bundled).
- **Structure:** 2 source modules (`lib.rs`, `main.rs`) + 1 integration test file.
- **Interfaces:** 6 HTTP routes (health + full books CRUD), 2 exported library functions (`open_db`, `app`).
- **Notable:** Clean separation of library (`lib.rs`) from binary (`main.rs`), enabling in-memory `:memory:` DB testing via `oneshot`; unified `ApiError` enum for status/JSON error mapping; single `Arc<Mutex<Connection>>` serializes all DB access.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
