# Summary: effort=default_language=go_model=claude-opus-5-5_prompt=neutral · rep 2

- **Shape:** Go `net/http` (1.22+ method/path routing) CRUD service with SQLite persistence via the pure-Go `modernc.org/sqlite` driver.
- **Structure:** 3 source modules + 1 test file (6 test functions), README included.
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter); `Store` persistence API with 7 methods.
- **Notable:** No CGO needed; extras beyond spec — graceful shutdown, `Location` header on create, `DisallowUnknownFields`, 1 MiB body cap, ISBN/year validation, case-insensitive author filter.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
