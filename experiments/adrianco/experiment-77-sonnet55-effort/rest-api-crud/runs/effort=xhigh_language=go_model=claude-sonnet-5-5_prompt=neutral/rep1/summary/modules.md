# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Config from env, server start-up, graceful SIGINT/SIGTERM shutdown | `main()`, `run()` |
| internal/books/books.go | Book model, `Input` validation rules (`Clean`) | `Book`, `Input`, `ValidationError`, `Input.Clean()` |
| internal/books/store.go | SQLite-backed persistence + schema | `Store`, `Open()`, `Create/Get/List/Update/Delete`, `Ping`, `ErrNotFound`, `MemoryPath` |
| internal/api/api.go | HTTP routing, handlers, JSON helpers, logging/recovery middleware | `New()`, `Store` (interface) |
| internal/books/store_test.go | Store + validation unit tests | 10 test functions |
| internal/api/api_test.go | Full HTTP API integration tests via httptest | 12 test functions |
