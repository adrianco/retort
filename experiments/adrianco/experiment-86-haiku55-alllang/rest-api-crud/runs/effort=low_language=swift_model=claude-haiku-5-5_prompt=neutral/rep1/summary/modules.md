# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/BookAPI/Book.swift | Models and input validation | `Book`, `BookInput`, `BookDraft`, `ValidationError`, `BookValidator` |
| Sources/BookAPI/BookStore.swift | SQLite-backed storage (actor) | `BookStore`, `create`, `list`, `find`, `update`, `delete` |
| Sources/BookAPI/Routes.swift | HTTP routes and application builder | `buildRouter(store:)`, `buildApplication(store:host:port:)` |
| Sources/BookAPIServer/main.swift | Executable entry point | top-level async main |
| Sources/CSQLite/module.modulemap | System library shim mapping `sqlite3` | module `CSQLite` |
| Sources/CSQLite/shim.h | C header include for sqlite3 | — |
| Tests/BookAPITests/BookAPITests.swift | HTTP integration tests via HummingbirdTesting | 8 test functions |
| Tests/BookAPITests/BookStoreTests.swift | Store + validator unit tests | 5 test functions |
