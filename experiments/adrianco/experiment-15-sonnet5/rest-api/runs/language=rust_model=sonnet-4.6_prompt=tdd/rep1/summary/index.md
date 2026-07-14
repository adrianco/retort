# Summary: language=rust_model=sonnet-4.6_prompt=tdd · rep 1

- **Shape:** Axum 0.7 REST API with rusqlite (bundled SQLite), in-memory DB, UUID ids.
- **Structure:** 4 source modules (main/handlers/db/models), tests co-located in `main.rs` (10 integration tests).
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), 0 CLI commands, `build_app()` exported for testing.
- **Notable:** Clean separation of handlers/db/models; parameterized SQL; `?author=` filter implemented at the SQL layer. Uses `422` for validation (spec examples suggest `400`); SQLite opened in-memory so data is non-durable.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
