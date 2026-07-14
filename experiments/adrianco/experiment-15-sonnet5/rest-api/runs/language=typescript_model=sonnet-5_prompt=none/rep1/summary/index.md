# Summary: language=typescript · model=sonnet-5 · prompt=none · rep 1

- **Shape:** TypeScript/Express REST API backed by Node's built-in `node:sqlite` (`DatabaseSync`).
- **Structure:** 5 source modules + 1 test file (8 integration tests).
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), 3 exported functions, 1 `books` table.
- **Notable:** Uses the built-in `node:sqlite` module rather than `better-sqlite3` (dodges native-compile issues); clean separation of app factory / DB / validation / types; parameterized queries throughout; dependency-injected DB makes tests use `:memory:`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
