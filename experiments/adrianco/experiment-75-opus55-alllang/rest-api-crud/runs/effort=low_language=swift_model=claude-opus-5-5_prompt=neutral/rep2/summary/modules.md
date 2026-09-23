# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/BookAPI/BookStore.swift | SQLite-backed book repository (thread-safe via NSLock) | `Book`, `BookStore`, `.list/.get/.create/.update/.delete` |
| Sources/BookAPI/Router.swift | Transport-independent request routing + validation → JSON responses | `Router`, `HTTPResponse`, `Router.handle(method:target:body:)` |
| Sources/BookAPI/Server.swift | Minimal HTTP/1.1 server on Network.framework | `HTTPServer`, `.start()/.stop()`, `.port` |
| Sources/BookServer/main.swift | Executable entry point; reads PORT/DB_PATH env | top-level program |
| Tests/BookAPITests/BookAPITests.swift | XCTest unit + integration tests | 5 test functions |
