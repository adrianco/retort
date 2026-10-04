# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entry: config from env, opens store, serves HTTP with graceful shutdown | `main()`, `getenv()` |
| handlers.go | HTTP handler: routing, JSON I/O, request decode/validation | `NewHandler()`, `Server`, `createBook`/`listBooks`/`getBook`/`updateBook`/`deleteBook`/`health` |
| store.go | SQLite persistence layer and `Book` model | `NewStore()`, `Store`, `Book`, `ErrNotFound`, `Create`/`List`/`Get`/`Update`/`Delete`/`Ping` |
| handlers_test.go | API integration tests over an in-memory store | 8 test functions |
