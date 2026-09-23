# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Config from env, server startup, graceful shutdown | `main()`, `getenv()` |
| handlers.go | Routes, input validation, JSON responses | `Server`, `Routes()`, `createBook`/`listBooks`/`getBook`/`updateBook`/`deleteBook`, `health`, `validISBN` |
| store.go | SQLite storage: schema + CRUD queries | `Store`, `OpenStore()`, `Book`, `ErrNotFound`, `Create/List/Get/Update/Delete`, `Ping` |
| main_test.go | Integration tests against a temp SQLite DB | 7 test functions (+ 8 validation subtests) |
