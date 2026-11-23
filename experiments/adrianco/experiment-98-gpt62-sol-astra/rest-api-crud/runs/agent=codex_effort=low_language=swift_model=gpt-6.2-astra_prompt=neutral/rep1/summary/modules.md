# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Books.swift | Data model, SQLite-backed store, and HTTP routing/validation logic | `Fields`, `Book`, `APIError`, `Database`, `route(_:_:_:db:)` |
| Server.swift | POSIX-socket HTTP/1.1 server: request parsing, response framing, `@main` listener | `serve(_:db:)`, `Server.main()` |
| Tests.swift | XCTest integration tests exercising routes, persistence, validation, health, and raw HTTP | `BookAPITests` (5 test functions) |
| Package.swift | SwiftPM manifest; system-library target for SQLite, no external package deps | `BooksAPI`, `BooksTests` targets |
| CSQLite/module.modulemap, CSQLite/shim.h | System library shim exposing libsqlite3 to Swift | — |
| Makefile | build/run/test targets (`swift build/run/test --disable-sandbox`) | — |
| README.md | Setup and run instructions, route table | — |
