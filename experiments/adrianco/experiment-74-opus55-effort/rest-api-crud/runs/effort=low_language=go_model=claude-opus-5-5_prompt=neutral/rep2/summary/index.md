# Summary: effort=low_language=go_model=claude-opus-5-5_prompt=neutral · rep 2

- **Shape:** Go `net/http` CRUD API with SQLite persistence (`modernc.org/sqlite`, pure-Go, no cgo).
- **Structure:** 2 source modules (main.go, server.go) + 1 test file.
- **Interfaces:** 6 HTTP routes (5 CRUD + health), 1 exported constructor.
- **Notable:** Uses Go 1.22+ pattern-routing `ServeMux` (no third-party web framework); hardened decode (`DisallowUnknownFields`, `MaxBytesReader`); health check pings the DB; compact single-handler-per-route design at low effort.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
