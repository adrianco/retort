# Summary: effort=high language=go model=claude-haiku-5-5 prompt=neutral · rep 3

- **Shape:** Go `net/http` (stdlib 1.22+ method-pattern router) CRUD service backed by pure-Go embedded SQLite (`modernc.org/sqlite`).
- **Structure:** 4 source modules + 3 test files (16 test functions); clean separation of model / store / HTTP / main.
- **Interfaces:** 6 HTTP routes (full CRUD + `?author=` filter + `/health`), 1 CLI binary, 7 exported package symbols.
- **Notable:** Goes well beyond spec — ISBN-10/13 checksum validation, unknown-field rejection, 1 MiB body cap, `Location` header on create, graceful shutdown, single-connection pool to dodge SQLite lock errors.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
