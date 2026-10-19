# Summary: agent=hermes-0222 language=go model=llamacpp/Holo4-35B-A3B prompt=neutral stack=holo4 · rep 2

- **Shape:** Go `net/http` CRUD service backed by SQLite via the pure-Go `modernc.org/sqlite` driver.
- **Structure:** 4 source modules + 1 test file (8 tests).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD); no library or CLI surface.
- **Notable:** Clean idiomatic standard-library structure (no web framework), parameterized SQL, `409` on ISBN conflict and graceful shutdown beyond spec; but `PUT` ignores/omits `isbn` and all README curl examples use the wrong port (8080 vs the code's 8000 default).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
