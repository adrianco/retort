# Summary: effort=default language=rust model=claude-fable-5-1 prompt=none · rep 1

- **Shape:** Axum 0.8 REST API with SQLite persistence via `rusqlite` (bundled).
- **Structure:** 2 source modules (`lib.rs`, `main.rs`), 1 test file (7 tests).
- **Interfaces:** 6 HTTP routes; 3 exported library symbols (`app`, `open_db`, `Book`).
- **Notable:** Clean separation of lib/bin; typed `ApiError` → status mapping; poison-tolerant `Mutex<Connection>`; env-configurable host/port/db path with graceful shutdown; validation returns 422 (not 400) for missing fields.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
