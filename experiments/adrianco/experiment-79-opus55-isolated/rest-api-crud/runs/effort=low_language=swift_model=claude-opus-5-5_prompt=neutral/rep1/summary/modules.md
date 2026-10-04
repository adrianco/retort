# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/BookAPI/Book.swift | Book model + validated `BookInput` with JSON parsing/validation | `Book`, `BookInput`, `BookInput.parse(json:)`, `ValidationError` |
| Sources/BookAPI/BookStore.swift | SQLite-backed CRUD storage, thread-safe via NSLock | `BookStore`, `create`, `list`, `get`, `update`, `delete` |
| Sources/BookAPI/Router.swift | Maps HTTP requests to store operations (transport-independent) | `Router`, `handle(_:)` |
| Sources/BookAPI/HTTP.swift | HTTP request/response types, JSON helpers, HTTP/1.1 parser | `HTTPRequest`, `HTTPResponse`, `HTTPParser.parse(_:)` |
| Sources/BookAPI/Server.swift | Minimal HTTP/1.1 server on Network.framework | `Server`, `start()`, `stop()` |
| Sources/bookapi-server/main.swift | Executable entry point; reads PORT/DB_PATH env | top-level `main` |
| Tests/BookAPITests/BookAPITests.swift | Router, store, parser and end-to-end HTTP tests | 13 test functions across 4 XCTestCase classes |
