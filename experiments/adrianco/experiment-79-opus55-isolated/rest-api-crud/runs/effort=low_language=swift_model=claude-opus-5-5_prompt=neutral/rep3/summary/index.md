# Summary: rest-api-crud · effort=low language=swift model=claude-opus-5-5 prompt=neutral · rep 3

- **Shape:** Swift REST API with zero third-party dependencies — HTTP server on Network.framework, storage on the system `sqlite3` C library.
- **Structure:** 6 source modules (BookAPI library + BookServer executable), 1 test file (13 tests across 4 XCTestCase classes).
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter), ~5 exported types.
- **Notable:** Hand-rolled HTTP/1.1 parser with body-size limits and `Location`/`Allow` headers; validation uses `422` (Unprocessable Entity) for field failures and `400` for malformed bodies; SQLi-safe bound parameters; thread-safe store via `NSLock`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
