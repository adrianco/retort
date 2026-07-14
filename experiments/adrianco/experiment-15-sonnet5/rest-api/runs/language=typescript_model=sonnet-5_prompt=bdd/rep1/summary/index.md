# Summary: language=typescript · model=sonnet-5 · prompt=bdd · rep 1

- **Shape:** TypeScript + Express REST API with SQLite persistence via Node's built-in `node:sqlite` (no native build dependency).
- **Structure:** 5 source modules + 1 test file (14 tests).
- **Interfaces:** 6 HTTP routes (5 CRUD on /books + /health); 3 exported library functions.
- **Notable:** Clean separation (app / db / validation / types / server); DB is dependency-injected into `createApp` so tests use `:memory:`. Parameterized SQL throughout. Partial-validation path for PUT. Chose `node:sqlite` over `better-sqlite3` to avoid native builds — requires Node ≥ 22.5.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
