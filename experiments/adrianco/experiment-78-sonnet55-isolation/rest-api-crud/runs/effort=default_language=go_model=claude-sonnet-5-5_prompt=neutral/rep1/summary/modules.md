# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, route wiring, request decoding/validation, handlers | `main()`, `NewServer(*Store) http.Handler`, `handlers` |
| store.go | SQLite persistence + `Book` model, schema bootstrap, CRUD queries | `Book`, `Store`, `NewStore(dsn)`, `Create/List/Get/Update/Delete` |
| main_test.go | HTTP integration tests via `httptest` against an in-memory DB | 4 test functions: `TestHealth`, `TestCRUD`, `TestValidation`, `TestListFilter` |
