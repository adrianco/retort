# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| book.go | Domain model, input cleaning, validation (incl. ISBN-10/13 check digits) | `Book`, `BookInput`, `ValidationError`, `(BookInput).Clean`, `(BookInput).Validate` |
| store.go | SQLite persistence layer (CRUD + author filter) | `Store`, `OpenStore`, `Create`, `Get`, `List`, `Update`, `Delete`, `Ping`, `ErrNotFound` |
| server.go | HTTP handler, routing, JSON encoding, status codes | `NewHandler`, `server`, request helpers (`readID`, `readBookInput`, `decodeJSON`, `writeJSON`, `writeError`) |
| cmd/bookapi/main.go | Executable entry point: flag/env config, graceful shutdown | `main`, `run` |
| book_test.go | Validation + ISBN unit tests | 3 test functions |
| store_test.go | Store CRUD / not-found / filter tests | 3 test functions |
| api_test.go | End-to-end HTTP handler tests | 10 test functions |
