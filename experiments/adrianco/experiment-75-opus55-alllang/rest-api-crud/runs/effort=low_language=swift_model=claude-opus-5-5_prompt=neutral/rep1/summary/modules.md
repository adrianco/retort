# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/BookAPI/Database.swift | SQLite-backed, thread-safe book store + `Book` model | `Book`, `BookStore`, `create/list/get/update/delete` |
| Sources/BookAPI/Router.swift | Transport-independent request → response routing, validation, JSON encoding | `HTTPRequest`, `HTTPResponse`, `Router.handle` |
| Sources/BookAPI/HTTPServer.swift | Minimal HTTP/1.1 server on Network.framework | `HTTPServer`, `start()`, `stop()`, `parse()` |
| Sources/BookServer/main.swift | Executable entry point; wires store + server from env vars | top-level `main` |
| Tests/BookAPITests/BookAPITests.swift | Swift Testing suite (router + HTTP parse) | 6 `@Test` functions |
| Package.swift | SwiftPM manifest; links system `sqlite3` | 3 targets |
