# Summary: agent=hermes-local language=typescript prompt=ATDD · rep 2

- **Shape:** TypeScript Express REST API with better-sqlite3 (embedded SQLite) persistence.
- **Structure:** 3 source modules (app / db / validation), 2 test files (34 tests total).
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), 1 `books` SQLite table, ~10 exported DB/validation functions.
- **Notable:** Clean ATDD split — acceptance tests drive the public HTTP interface only, unit tests cover validation + DB layer. Carries an unused module-global DB handle (`setAppDb`/`getAppDb`/`shutdownDb`) alongside the closure-captured `db`, and a create/read representation mismatch for omitted `year`/`isbn` (`0`/`""` in POST response vs `null` on `GET`).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
