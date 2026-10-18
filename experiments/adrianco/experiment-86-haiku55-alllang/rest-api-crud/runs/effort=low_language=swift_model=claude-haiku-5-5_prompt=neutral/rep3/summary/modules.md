# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/BookAPI/Book.swift | Models, input decoding, validation | `Book`, `BookInput`, `ValidBook`, `BookValidator.validate` |
| Sources/BookAPI/BookStore.swift | SQLite-backed persistence, serialized via lock | `BookStore`, `create`/`find`/`list`/`update`/`delete` |
| Sources/BookAPI/Router.swift | Maps HTTP requests to book operations (socket-independent) | `BookRouter.handle`, `HTTPRequest`, `HTTPResponse` |
| Sources/BookAPI/HTTPServer.swift | HTTP/1.1 parsing + serving on Network.framework | `HTTPServer.start`/`stop`, `HTTPServer.parse` |
| Sources/BookAPIServer/main.swift | Executable entry point; env-configured port/db path | top-level `main` |
| Tests/BookAPITests/BookAPITests.swift | Router-level + parser unit/integration tests | 11 test functions |
