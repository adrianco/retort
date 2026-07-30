# Summary: claude-code · claude-opus-5 · python (neutral, effort=max) · rep 2

- **Shape:** Flask REST API with a hand-rolled `sqlite3` data layer (no ORM), organised as an application-factory package.
- **Structure:** 8 source modules (~1,176 LOC) + 7 test modules (~1,175 LOC, 104 test functions).
- **Interfaces:** 9 HTTP routes (full CRUD + PATCH, /health, /, /openapi.json), plus `X-Total-Count` and `Location` headers.
- **Notable:** Well beyond spec — layered architecture (routes/repository/db/validation/errors), PATCH, filtering/sorting/pagination, OpenAPI spec, WAL + shared-cache in-memory handling, and unusually careful edge-case validation (control chars, NUL, SQLite INT bounds, blank CHECK constraints).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
