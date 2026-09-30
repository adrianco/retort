# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server: route table, JSON helpers, request decoding/validation, handlers, process entry point | `main()`, `newHandler()`, `server` (`health`, `create`, `list`, `get`, `update`, `delete`), `decodeBook()`, `pathID()`, `writeJSON()`, `writeErr()` |
| store.go | "Store persists books in SQLite" — opens/migrates the DB and runs the CRUD queries | `Book`, `Store`, `NewStore()`, `Store.Create/List/Get/Update/Delete/Ping/Close`, `errNotFound` |
| main_test.go | HTTP-level integration tests against an in-memory SQLite store via `httptest` | 4 test functions: `TestHealth`, `TestCRUD`, `TestListAuthorFilter`, `TestValidationAndErrors` |
| go.mod | Module `bookapi`, Go 1.26.6, `modernc.org/sqlite` v1.60.0 | — |
| README.md | Setup, run, test instructions and endpoint table | — |
