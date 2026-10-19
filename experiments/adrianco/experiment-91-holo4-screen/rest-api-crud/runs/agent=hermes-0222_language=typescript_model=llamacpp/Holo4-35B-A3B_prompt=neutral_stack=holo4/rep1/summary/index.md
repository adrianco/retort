# Summary: typescript · llamacpp/Holo4-35B-A3B · neutral · rep 1

- **Shape:** TypeScript/Express REST API with better-sqlite3 persistence.
- **Structure:** 5 source modules + 1 test file (14 integration tests).
- **Interfaces:** 6 HTTP routes (full books CRUD + ?author= filter + /health), one `books` table.
- **Notable:** Replaces `express.json()` with a hand-rolled `parseBody` stream parser; create-validation is stricter than spec (requires year+isbn too); tests run against a real ephemeral http server rather than supertest.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
