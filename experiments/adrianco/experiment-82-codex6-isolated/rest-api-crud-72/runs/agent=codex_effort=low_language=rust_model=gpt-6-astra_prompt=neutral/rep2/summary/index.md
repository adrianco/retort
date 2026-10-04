# Summary: rest-api-crud · codex/gpt-6-astra/rust/neutral · rep 2

- **Shape:** Rust Axum REST API over embedded SQLite (rusqlite, bundled), async handlers with blocking DB thread pool.
- **Structure:** 3 source modules (lib.rs, main.rs, tests.rs), 1 test module with 6 tests.
- **Interfaces:** 6 HTTP routes (CRUD + list-filter + health) + 2 fallbacks; 1 exported `app()` builder and `Book` type.
- **Notable:** Two-layer validation (app-side trim/non-blank + SQL `CHECK`), uniform `{"error":...}` JSON, `Location` header on create, graceful shutdown, `--locked` builds, SQL-injection-safe parameterized queries (test explicitly probes `' OR 1=1--`). Single global `Mutex<Connection>` serializes DB access.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
