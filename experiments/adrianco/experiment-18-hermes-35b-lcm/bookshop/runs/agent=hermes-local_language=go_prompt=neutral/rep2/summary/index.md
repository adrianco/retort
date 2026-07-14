# Summary: agent=hermes-local language=go prompt=neutral · rep 2

- **Shape:** Go `net/http` CRUD REST API over SQLite (`modernc.org/sqlite`, pure-Go, no CGO), no web framework.
- **Structure:** 4 source modules (main, handlers, database, model) + 1 test file.
- **Interfaces:** 6 HTTP routes (5 `/books` CRUD + `/health`); one `books` table.
- **Notable:** Clean 4-file layered split (handler / db / model). Hand-rolled router. Partial-update via pointer DTOs. Validation is create-only; author filter is a substring `LIKE`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
