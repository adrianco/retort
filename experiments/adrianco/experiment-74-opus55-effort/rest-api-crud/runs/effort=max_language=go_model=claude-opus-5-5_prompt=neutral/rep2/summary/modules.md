# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entry: config parsing, listener, graceful shutdown | `main()`, `run()`, `parseConfig()` |
| server.go | HTTP API: routing, handlers, middleware, JSON/error encoding | `NewServer()`, `Server.ServeHTTP`, `routes()` |
| store.go | SQLite persistence layer (CRUD) | `OpenStore()`, `Store.CreateBook/GetBook/ListBooks/UpdateBook/DeleteBook` |
| book.go | Domain model + request validation | `Book`, `BookInput`, `BookInput.Validate`, `ValidationError` |
| main_test.go | Config + lifecycle tests | 3 test functions |
| book_test.go | Model/validation unit tests | 3 test functions |
| store_test.go | Store CRUD + persistence + concurrency tests | 6 test functions |
| server_test.go | HTTP handler/integration tests | 10 test functions |
