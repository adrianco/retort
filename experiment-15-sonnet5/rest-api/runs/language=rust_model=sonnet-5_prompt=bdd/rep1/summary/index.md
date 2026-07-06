# Summary: language=rust · model=sonnet-5 · prompt=bdd · rep 1

- **Shape:** Rust axum 0.7 REST API with rusqlite + r2d2 SQLite connection pooling.
- **Structure:** 6 source modules (main/lib/db/models/handlers/error), 1 test file.
- **Interfaces:** 6 HTTP routes (5 CRUD + health), 3 exported library functions, 1 `books` table.
- **Notable:** Clean layered separation with a dedicated `AppError` → HTTP-status mapping; library/binary split lets tests drive the router in-process against an in-memory DB. BDD prompt honored — all 11 tests use Given/When/Then structure and behavior-named functions.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
