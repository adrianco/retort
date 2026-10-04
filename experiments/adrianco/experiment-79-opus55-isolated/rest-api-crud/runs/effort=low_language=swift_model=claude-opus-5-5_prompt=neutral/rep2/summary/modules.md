# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/BookAPI/BookStore.swift | SQLite-backed persistence (thread-safe via NSLock) | `Book`, `BookInput`, `BookStore`, `StoreError` |
| Sources/BookAPI/App.swift | Routing, JSON responses, input validation (transport-independent) | `BookApp`, `HTTPRequest`, `HTTPResponse` |
| Sources/BookAPI/Server.swift | Minimal HTTP/1.1 server on POSIX sockets | `HTTPServer`, `ServerError` |
| Sources/bookapi-server/main.swift | Executable entry point; reads PORT/HOST/DB_PATH env | (top-level program) |
| Tests/BookAPITests/BookAPITests.swift | Unit + end-to-end tests | 12 test functions (`BookAppTests`, `HTTPServerTests`) |
