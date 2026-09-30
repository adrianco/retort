# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entrypoint: flags/env, opens store, runs `net/http` server with graceful shutdown | `main`, `run` |
| internal/store/store.go | SQLite-backed book repository (CRUD, author filter, persistence) | `Store`, `Open`, `Book`, `Input`, `ErrNotFound`, `Create/Get/List/Update/Delete/Ping/Close` |
| internal/api/api.go | HTTP handler: routing, method dispatch, endpoint handlers, error mapping | `New`, `BookStore` (interface), `route` |
| internal/api/request.go | Request decoding + validation for POST/PUT bodies | `readBook`, `bookRequest.validate`, `decodeJSON` |
| internal/api/response.go | JSON response writing, request-logging + panic-recovery middleware | `writeJSON`, `writeError`, `requestLogger`, `recoverer` |
| internal/store/store_test.go | Store unit tests (CRUD, filter, persistence, concurrency) | 10 test functions |
| internal/api/api_test.go | API integration tests (all endpoints, validation, errors) | 19 test functions |
