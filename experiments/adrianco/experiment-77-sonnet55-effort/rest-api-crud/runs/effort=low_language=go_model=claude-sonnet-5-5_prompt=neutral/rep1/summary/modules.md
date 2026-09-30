# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, routing, handlers, validation | `newHandler()`, `main()`, `server` |
| store.go | SQLite persistence + Book model | `Book`, `Store`, `NewStore()`, `Create/List/Get/Update/Delete` |
| main_test.go | HTTP integration tests | 4 test functions |
