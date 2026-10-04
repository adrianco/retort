# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status} \| 503` | `main.go:Routes` (inline) |
| POST | /books | `201 Book \| 400` | `main.go:books` |
| GET | /books | `200 [Book]` (opt `?author=`) | `main.go:listBooks` |
| GET | /books/{id} | `200 Book \| 404` | `main.go:bookByID` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `main.go:bookByID` |
| DELETE | /books/{id} | `204 \| 404` | `main.go:bookByID` |

Routing uses Go 1.22 method-pattern mux (`GET /health`) plus prefix handlers
(`/books`, `/books/`) that switch on `r.Method`.

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null),
author (TEXT not null), year (INTEGER default 0), isbn (TEXT default '').

## Library API

`NewAPI(db *sql.DB) (*API, error)` — creates the table and returns the handler
factory; `(*API).Routes() http.Handler` — the mux.
