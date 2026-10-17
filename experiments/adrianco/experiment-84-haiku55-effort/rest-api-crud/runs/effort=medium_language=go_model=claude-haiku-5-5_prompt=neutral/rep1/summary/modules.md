# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Entry point: flags/env config, HTTP server with timeouts, graceful shutdown | `main`, `envOr` |
| server.go | Routes, HTTP handlers, request decoding/validation, JSON helpers | `NewServer`, `Server.ServeHTTP` |
| store.go | SQLite persistence (pure-Go driver), CRUD + schema | `OpenStore`, `Store` (`Create`/`Get`/`List`/`Update`/`Delete`/`Ping`) |
| book.go | Book model, input normalisation, validation, ISBN-10/13 check digits | `Book`, `BookInput`, `Validate`, `validISBN` |
| book_test.go | Unit tests for validation, ISBN, normalisation | 6 test functions |
| server_test.go | HTTP integration tests over a real SQLite temp DB | 12 test functions |
