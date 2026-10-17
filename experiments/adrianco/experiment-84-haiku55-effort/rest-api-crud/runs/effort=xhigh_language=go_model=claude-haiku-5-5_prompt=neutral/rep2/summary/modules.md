# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entry: flags, opens store, serves HTTP with graceful shutdown | `main`, `run` |
| internal/book/book.go | Book domain type, input normalization & validation (incl. ISBN check digits) | `Book`, `Input`, `FieldErrors`, `Input.Normalize`, `Input.Validate` |
| internal/store/store.go | SQLite-backed repository: schema, CRUD, author filter | `Store`, `ErrNotFound`, `Open`, `Create`, `Get`, `List`, `Update`, `Delete`, `Ping`, `Close` |
| internal/server/server.go | HTTP routing, health handler, request-logging & status-recorder middleware | `Server`, `New`, `Handler`, `health` |
| internal/server/books.go | CRUD route handlers; input decode, path-id parse, error mapping | `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook` |
| internal/server/respond.go | JSON response helpers, strict JSON decoder, error body shape | `writeJSON`, `writeError`, `writeValidationError`, `decodeJSON` |
| internal/book/book_test.go | Domain validation/normalization tests | 5 test functions |
| internal/store/store_test.go | Store CRUD / filter / not-found tests | 9 test functions |
| internal/server/server_test.go | HTTP handler integration tests | 10 test functions |
