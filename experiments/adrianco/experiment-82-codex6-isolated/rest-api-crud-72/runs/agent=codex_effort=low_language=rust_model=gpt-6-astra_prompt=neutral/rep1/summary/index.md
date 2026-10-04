# Summary: rest-api-crud · agent=codex effort=low language=rust model=gpt-6-astra prompt=neutral · rep 1

- **Shape:** Rust Axum REST API with embedded SQLite (rusqlite, bundled), single-crate lib + bin.
- **Structure:** 3 source modules (`lib.rs`, `main.rs`, `tests.rs`), 1 test module (5 tests).
- **Interfaces:** 6 book/health HTTP routes + fallbacks; 1 exported `app()` builder; 1 `books` table.
- **Notable:** Concise, idiomatic; SQLite work dispatched to the blocking pool behind a mutex; table-level CHECK constraints mirror app validation; graceful shutdown; tests cover CRUD lifecycle, filtering, validation, JSON errors, and file-DB persistence across reopen.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
