# Summary: agent=hermes-local language=python model=mlxlocal/Qwen3.6-35B-A3B prompt=neutral stack=m35 · rep 1

- **Shape:** Flask REST API with raw sqlite3 (stdlib) storage
- **Structure:** 1 source module, 1 test file (16 tests), README + requirements
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 `books` table
- **Notable:** Clean per-request connection handling via Flask `g`/`teardown_appcontext`; validation on both create and update; no ORM, no pagination.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
