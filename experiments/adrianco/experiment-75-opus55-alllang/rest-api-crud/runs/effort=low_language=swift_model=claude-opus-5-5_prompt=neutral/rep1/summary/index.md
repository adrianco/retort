# Summary: rest-api-crud · effort=low language=swift model=claude-opus-5-5 prompt=neutral · rep 1

- **Shape:** Swift REST API — hand-rolled HTTP/1.1 on Network.framework, SQLite via system `libsqlite3`, zero third-party dependencies.
- **Structure:** 4 source modules (2 targets: `BookAPI` library + `BookServer` executable), 1 test file (6 `@Test` cases, Swift Testing).
- **Interfaces:** 7 HTTP routes (6 book/health + a 405 fallback), 3 exported library types (`BookStore`, `Router`, `HTTPServer`).
- **Notable:** Clean separation of transport (`HTTPServer`) from routing (`Router`) makes the handler unit-testable without opening a socket; thread-safe store behind a single `NSLock`; no external deps at all.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
