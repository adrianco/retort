# Summary: agent=hermes-local language=python prompt=neutral · rep 1

- **Shape:** FastAPI REST API with raw-sqlite3 persistence (no ORM), Pydantic request/response models.
- **Structure:** 1 app module + 1 test module (15 tests), README.
- **Interfaces:** 6 HTTP routes (5 CRUD + /health), 3 Pydantic models, `books` SQLite table.
- **Notable:** Clean per-request connection handling with `try/finally`; WAL mode; partial updates via `exclude_unset`. Validation returns FastAPI's 422 rather than the spec's suggested 400. No dependency manifest (deps listed only in README).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
