# Summary: effort=medium language=go model=claude-haiku-5-5 prompt=neutral · rep 3

- **Shape:** Go `net/http` CRUD service backed by SQLite via the pure-Go `modernc.org/sqlite` driver (no cgo).
- **Structure:** 4 source modules, 3 test files (17 test functions).
- **Interfaces:** 6 HTTP routes (CRUD + list-filter + health), plus a small exported store/validation API.
- **Notable:** goes beyond the spec — ISBN-10/13 checksum validation, ISBN normalization + uniqueness (409), JSON 405 with `Allow` header, 1 MiB body cap, graceful shutdown. Uses Go 1.22 `ServeMux` method+path patterns instead of a third-party router.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
