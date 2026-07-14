# Summary: agent=hermes-local language=go prompt=neutral · rep 1

- **Shape:** Go `net/http` + gorilla/mux REST CRUD API backed by SQLite (mattn/go-sqlite3, WAL mode).
- **Structure:** 4 source modules + 1 test file (14 test functions).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 `books` table; partial-update PUT via pointer DTO.
- **Notable:** Clean layering (handlers/db/models split); real embedded persistence rather than in-memory; timestamp read-back layout mismatch is the one latent flaw.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
