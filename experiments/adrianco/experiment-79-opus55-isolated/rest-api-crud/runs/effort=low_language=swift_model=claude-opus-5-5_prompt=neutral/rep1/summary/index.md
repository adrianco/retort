# Summary: rest-api-crud (effort=low, language=swift, model=claude-opus-5-5, prompt=neutral) · rep 1

- **Shape:** Swift REST API with a hand-rolled HTTP/1.1 server on Network.framework and SQLite storage via the system `sqlite3` C library — zero third-party dependencies.
- **Structure:** 6 source modules (model, store, router, HTTP, server, main) + 1 test file with 13 tests across 4 XCTestCase classes.
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 SQLite table, several exported library types.
- **Notable:** Transport-independent `Router` enables both direct unit tests and real-socket integration tests; parameterized SQL; thread-safe store; PUT does full-resource replacement.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
