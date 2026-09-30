# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: reads `ADDR`/`DB_PATH` env, opens store, runs `http.Server` | `main`, `getenv` |
| store.go | SQLite persistence via `modernc.org/sqlite`; schema + CRUD | `Book`, `Store`, `NewStore`, `Create`, `List`, `Get`, `Update`, `Delete`, `Ping`, `ErrNotFound` |
| handlers.go | HTTP router, JSON encoding, request validation, route handlers | `NewHandler`, `Server`, `writeJSON`, `decodeBook`, `pathID` |
| handlers_test.go | Integration tests over the HTTP handler + store | 8 test functions (`TestHealth`, `TestCreateAndGet`, `TestValidation`, `TestListAndAuthorFilter`, `TestUpdate`, `TestDelete`, `TestNotFoundAndBadID`, `TestPersistsAcrossReopen`) |
