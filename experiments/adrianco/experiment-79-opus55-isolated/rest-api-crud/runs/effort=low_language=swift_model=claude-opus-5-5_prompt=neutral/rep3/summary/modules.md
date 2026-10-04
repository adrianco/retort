# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/BookAPI/Book.swift | `Book` model + `BookInput` request parsing/validation | `Book`, `Book.json`, `BookInput`, `BookInput.parse` |
| Sources/BookAPI/BookStore.swift | SQLite-backed CRUD storage, thread-safe via `NSLock` | `BookStore`, `create`, `list`, `get`, `update`, `delete` |
| Sources/BookAPI/HTTP.swift | HTTP/1.1 request parser + response builder | `HTTPRequest.parse`, `HTTPResponse.json`, `HTTPResponse.error`, `serialized` |
| Sources/BookAPI/Router.swift | Maps requests onto store operations | `Router`, `Router.handle` |
| Sources/BookAPI/Server.swift | Network.framework TCP listener, one request per connection | `Server`, `start`, `stop` |
| Sources/BookServer/main.swift | Executable entry point; reads `PORT`/`DB_PATH` env | top-level `main` |
| Tests/BookAPITests/BookAPITests.swift | Unit + integration tests | 13 test functions across 4 XCTestCase classes |
