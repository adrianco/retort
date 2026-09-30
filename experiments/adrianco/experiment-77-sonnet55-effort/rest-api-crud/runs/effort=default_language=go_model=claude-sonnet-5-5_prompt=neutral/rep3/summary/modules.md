# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, routing, request decoding/validation, handlers | `main()`, `newHandler(*Store)`, `server` |
| store.go | SQLite persistence + `Book` model and migration | `Book`, `Store`, `NewStore()`, `Create/Get/List/Update/Delete`, `errNotFound` |
| main_test.go | HTTP integration tests against in-memory DB | 5 test functions |
