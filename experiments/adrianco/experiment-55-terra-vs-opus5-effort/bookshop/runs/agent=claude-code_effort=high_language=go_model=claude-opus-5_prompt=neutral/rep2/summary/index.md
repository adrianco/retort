# Summary: go · claude-opus-5 · effort=high · rep 2

- **Shape:** Go `net/http` (1.22+ method-pattern routing) REST CRUD API over a pure-Go SQLite store (`modernc.org/sqlite`).
- **Structure:** 4 source modules + 2 test files (~697 source LOC, ~613 test LOC).
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), one `books` SQLite table.
- **Notable:** No third-party web framework or CGO; layered store/HTTP split via sentinel errors; hardened beyond spec (panic recovery, body-size cap, strict JSON, graceful shutdown, timeouts, ISBN check-digit validation, duplicate-ISBN conflict). Validation failures return `422` rather than `400`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
