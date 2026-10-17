# Summary: effort=max · language=go · model=claude-haiku-5-5 · prompt=neutral · rep 1

- **Shape:** Go `net/http` CRUD REST API over on-disk SQLite (`modernc.org/sqlite`, pure-Go, no cgo).
- **Structure:** 4 source modules, 3 test files (19 test functions).
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter), 1 SQLite table.
- **Notable:** Clean layered split (handler / store / domain); strict JSON decoding with per-field validation errors; ISBN-10/13 check-digit validation and year-range checks beyond spec; graceful shutdown; `405`+`Allow` and JSON catch-all `404`; WAL + single-writer connection.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
