# Run Summary: rest-api-crud (Go, Opus 5.5, effort=low, rep3)

## Surface

A REST API for a book collection: CRUD over `/books`, an `?author=` list filter,
and a `/health` check, persisting to an embedded SQLite database and returning
JSON with appropriate HTTP status codes.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `main.go` | HTTP server, routing, handlers, DB open + schema, validation | `main()`, `NewServer(db)`, `OpenDB(path)`, `Server` (`create`/`list`/`get`/`update`/`delete`) |
| `main_test.go` | httptest-based integration tests over an in-memory DB | `TestHealth`, `TestCRUD`, `TestValidation`, `TestListAuthorFilter` |

Single-package (`package main`), no framework — Go 1.22+ `net/http`
method+pattern routing (`GET /books/{id}`, `r.PathValue("id")`).

## Interfaces

HTTP routes (all JSON):

| Method | Path | Description | Codes |
|--------|------|-------------|-------|
| GET | `/health` | Health check (pings DB) | 200 / 503 |
| POST | `/books` | Create book (`title`,`author` required; `year`,`isbn` optional) | 201 / 400 |
| GET | `/books` | List all; `?author=` case-insensitive full-name filter | 200 |
| GET | `/books/{id}` | Get one book | 200 / 404 / 400 |
| PUT | `/books/{id}` | Full replace (same validation as create) | 200 / 404 / 400 |
| DELETE | `/books/{id}` | Delete book | 204 / 404 / 400 |

Data schema — `books(id INTEGER PK AUTOINCREMENT, title TEXT NOT NULL,
author TEXT NOT NULL, year INTEGER, isbn TEXT)` via `modernc.org/sqlite`
(pure-Go, no CGO).

## Flow

`main()` reads `DB_PATH`/`PORT` env (defaults `books.db`/`8080`), calls
`OpenDB` (opens SQLite, `SetMaxOpenConns(1)`, creates table if absent), builds
the mux via `NewServer`, and serves. Handlers share `decodeBook` (JSON decode +
trim + required-field/year-range validation) and `pathID` (parse `{id}`),
returning JSON through `writeJSON`/`writeErr`.

## Notable choices

- `PUT` is a full replace, not a partial patch — omitted fields are cleared. Documented in README and the agent's summary.
- `?author=` matches the full name only (case-insensitive), not a substring.
- Empty author filter returns `[]`, not 404.
