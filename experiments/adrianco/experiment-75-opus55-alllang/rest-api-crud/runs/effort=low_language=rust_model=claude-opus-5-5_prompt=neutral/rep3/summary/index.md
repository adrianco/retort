# Summary: effort=low_language=rust_model=claude-opus-5-5_prompt=neutral · rep 3

- **Shape:** Axum 0.8 REST API over SQLite (rusqlite, bundled), single-crate lib+bin.
- **Structure:** 2 source modules (lib.rs, main.rs), 1 test file (4 integration tests).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 `books` table, ~4 exported symbols.
- **Notable:** Compact and idiomatic — validation trims input and bounds year, filter is `COLLATE NOCASE`, errors funnel through one `ApiError` enum. DB is a single `Arc<Mutex<Connection>>` (serialized access, `.unwrap()` on lock/bind).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
