# Summary: language=typescript_model=sonnet-4.6_prompt=tdd · rep 1

- **Shape:** TypeScript Express 5 REST API with `better-sqlite3` embedded storage.
- **Structure:** 3 source modules (app factory, server bootstrap, tests), 1 test file.
- **Interfaces:** 6 HTTP routes (5 CRUD + health), 1 exported factory function, 1 SQLite table.
- **Notable:** Clean dependency-injected app factory (`buildApp(db)`) enabling in-memory test DBs; 13 integration tests via supertest covering every endpoint plus 400/404 cases. TDD prompt followed (agent log documents red→green→refactor). Author filter is exact-match only.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
