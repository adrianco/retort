# Summary: rest-api-crud · effort=high language=python model=claude-opus-5-5 prompt=neutral · rep 2

- **Shape:** Pure-stdlib Python REST API (`wsgiref` WSGI + `sqlite3`), no third-party runtime deps.
- **Structure:** 6 source modules, 3 test files (37 test functions).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 CLI, 3 exported library symbols.
- **Notable:** Clean separation (routing / store / validation / server); thread-safe single SQLite connection; defensive edge-case handling (body-size cap, surrogate rejection, SQL-injection-safe author filter, HEAD/405/500 paths) well beyond the spec.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
