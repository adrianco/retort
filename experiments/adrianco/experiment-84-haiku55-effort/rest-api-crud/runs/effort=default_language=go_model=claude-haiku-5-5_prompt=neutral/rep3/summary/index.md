# Summary: effort=default_language=go_model=claude-haiku-5-5_prompt=neutral · rep 3

- **Shape:** Go `net/http` (1.22 method-based routing) CRUD service with pure-Go SQLite (`modernc.org/sqlite`) storage.
- **Structure:** 4 source modules, 2 test files (9 test functions total).
- **Interfaces:** 6 HTTP routes (5 CRUD + /health), 1 SQLite table, author query filter.
- **Notable:** No third-party web framework — stdlib router only. Hardening beyond spec: body-size cap, `DisallowUnknownFields`, trailing-content rejection, ISBN normalization + format check, partial-unique ISBN index with 409 conflict mapping, and graceful shutdown.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
