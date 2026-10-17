# Summary: effort=default language=python model=claude-haiku-5-5 prompt=neutral · rep 1

- **Shape:** Stdlib-only Python REST API (`http.server` + `sqlite3`), no third-party server deps.
- **Structure:** 1 source module, 1 test file (15 tests), README.
- **Interfaces:** 6 HTTP routes (5 CRUD + /health), 3 exported library symbols, 1 SQLite table.
- **Notable:** Zero-install stdlib approach; thorough validation (ISBN-10/13 normalisation, year bounds), 405+`Allow` handling, case-insensitive author filter, partial PUT. Single shared SQLite connection behind a lock.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
