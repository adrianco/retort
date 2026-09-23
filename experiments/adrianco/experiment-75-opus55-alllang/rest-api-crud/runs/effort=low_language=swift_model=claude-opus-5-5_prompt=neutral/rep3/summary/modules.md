# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/BookAPI/BookStore.swift | Thread-safe SQLite-backed book repository | `Book`, `StoreError`, `BookStore` (`create`, `list`, `get`, `update`, `delete`) |
| Sources/BookAPI/Router.swift | Transport-independent HTTP→store routing, validation, JSON encoding | `HTTPRequest`, `HTTPResponse`, `Router.handle(_:)` |
| Sources/BookAPI/HTTPServer.swift | Minimal HTTP/1.1 server on Network.framework | `HTTPServer` (`start()`, `parse(_:)`) |
| Sources/BookServer/main.swift | Executable entry point; reads PORT/DB_PATH env, starts server | top-level `main` |
| Tests/BookAPITests/RouterTests.swift | XCTest suite exercising the Router and HTTP parser | 7 test functions |
