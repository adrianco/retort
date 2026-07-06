# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Entrypoint: opens store, reads config from env, starts HTTP server | `main()` |
| models.go | `Book` type and required-field validation | `Book`, `Book.Validate()` |
| store.go | SQLite-backed data access layer (open/migrate + CRUD) | `Store`, `NewStore()`, `Create/List/Get/Update/Delete`, `ErrNotFound` |
| handlers.go | HTTP handlers + `ServeMux` routing, JSON/error helpers | `API`, `NewAPI()`, `Routes()`, `writeJSON`, `writeError` |
| handlers_test.go | Integration tests over the HTTP layer | 6 test functions |
