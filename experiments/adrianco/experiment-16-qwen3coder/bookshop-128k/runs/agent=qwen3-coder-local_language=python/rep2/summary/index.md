# Summary: agent=qwen3-coder-local language=python · rep 2

- **Shape:** FastAPI REST API with raw `sqlite3` persistence and pydantic models.
- **Structure:** 1 app module, 2 test files (pytest suite + standalone smoke script).
- **Interfaces:** 6 HTTP routes (5 CRUD + 1 health), 3 pydantic models exported.
- **Notable:** Clean per-request connection handling and parameterized queries; validation delegated to pydantic (missing fields → 422), leaving the hand-written 400 guard reachable only for empty strings. Synchronous DB access inside async handlers.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
