# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/BookAPI/Book.swift | Book model, request-input decoding, and validation | `Book`, `BookInput`, `ValidatedBook`, `ValidationError`, `BookInput.validated()` |
| Sources/BookAPI/BookStore.swift | Thread-safe SQLite-backed CRUD store | `BookStore`, `create`, `all`, `get`, `update`, `delete` |
| Sources/BookAPI/HTTP.swift | Raw HTTP/1.1 request parser and JSON response builder | `HTTPRequest`, `HTTPRequest.parse()`, `HTTPResponse`, `HTTPResponse.json/error/serialized` |
| Sources/BookAPI/Router.swift | Maps requests to store operations (networking-free, testable) | `Router`, `route(_:)` |
| Sources/BookAPI/HTTPServer.swift | TCP/HTTP server on Apple's Network framework | `HTTPServer`, `start`, `stop`, `port` |
| Sources/BookServer/main.swift | Executable entry point; reads PORT/DB_PATH env, boots server | top-level `main` |
| Tests/BookAPITests/RouterTests.swift | Router+store unit tests (no networking) | 13 test functions |
| Tests/BookAPITests/IntegrationTests.swift | End-to-end tests over a live TCP server | 4 test functions |
| Tests/BookAPITests/HTTPParsingTests.swift | HTTP parser + response serialization unit tests | 3 test functions |
