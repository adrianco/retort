# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| cmd/bookapi/main.go | Program entry: opens the store, wires the handler, runs an `http.Server` with env-based config (`ADDR`, `DB_PATH`) | `main`, `getenv` |
| internal/book/book.go | Book model, input validation, SQLite-backed store (schema create + CRUD) | `Book`, `ValidationError`, `Store`, `Open`, `Create`, `Get`, `List`, `Update`, `Delete`, `ErrNotFound` |
| internal/book/handler.go | HTTP layer: route registration, request decoding, JSON/error responses, status-code mapping | `Handler`, `NewHandler`, `ServeHTTP` |
| internal/book/book_test.go | Integration + unit tests over the handler and store | 5 test functions |
