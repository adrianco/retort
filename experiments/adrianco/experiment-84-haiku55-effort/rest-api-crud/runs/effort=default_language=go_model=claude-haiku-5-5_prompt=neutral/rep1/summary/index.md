# Summary: effort=default language=go model=claude-haiku-5-5 prompt=neutral · rep 1

- **Shape:** Go `net/http` (1.22 pattern router) CRUD REST API backed by pure-Go SQLite (`modernc.org/sqlite`).
- **Structure:** 4 source modules + 1 test file (10 test functions), ~510 non-test LoC.
- **Interfaces:** 6 HTTP routes (5 CRUD + health), 1 `books` table, clean store/handler/model separation.
- **Notable:** No external web framework; strict JSON decoding (MaxBytes, DisallowUnknownFields, trailing-token rejection), context propagation, graceful shutdown, and ISBN-10/13 checksum validation beyond the spec.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
