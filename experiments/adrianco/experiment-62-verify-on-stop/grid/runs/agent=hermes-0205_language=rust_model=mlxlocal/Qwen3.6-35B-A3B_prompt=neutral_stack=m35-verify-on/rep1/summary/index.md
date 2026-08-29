# Summary: Qwen3.6-35B-A3B · hermes-0205 · m35-verify-on · rep 1

- **Shape:** Rust actix-web REST CRUD API over rusqlite (SQLite), in-memory store.
- **Structure:** 3 source modules (main/database/models), tests co-located in `main.rs` and `database.rs` (21 test fns, no separate test dir).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 `books` table, 5 internal DB CRUD fns.
- **Notable:** REPAIR task. Tests pass (test_coverage=1.0) but the **live server never initializes its `books` table** — schema is created on a discarded connection (`create_connection("in-memory").ok()`), leaving a stray on-disk `in-memory` SQLite file in the workspace. This is the precise regression FEEDBACK.md said to fix; verify-on-stop did not catch it.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
