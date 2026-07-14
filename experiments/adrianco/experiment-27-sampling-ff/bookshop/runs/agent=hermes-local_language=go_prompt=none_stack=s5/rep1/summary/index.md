# Summary: agent=hermes-local language=go prompt=none stack=s5 · rep 1

- **Shape:** Go `net/http` CRUD REST API with SQLite persistence (`modernc.org/sqlite`, pure-Go driver).
- **Structure:** 3 source modules (main, handlers, models) + 1 test file (9 test functions).
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter); no CLI; store exposes 6 CRUD methods.
- **Notable:** Uses Go 1.22 method-aware routing for POST/GET on `/books`; pure-Go SQLite driver avoids cgo; handles duplicate-ISBN as `409`, partial-update via pointer fields; created_at/updated_at timestamps. Clean layering (handlers vs store).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
