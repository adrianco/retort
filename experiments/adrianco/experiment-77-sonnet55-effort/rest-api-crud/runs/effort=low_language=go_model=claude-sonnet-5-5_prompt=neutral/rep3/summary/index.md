# Architecture Summary

A small Go REST service for a book collection, stdlib `net/http` + SQLite via the
pure-Go `modernc.org/sqlite` driver. Three source files, one clean layer boundary.

## Modules

| File | Role |
|------|------|
| `main.go` | HTTP layer: route table (`newHandler`), request decoding/validation (`decodeBook`), per-endpoint handlers, JSON/error helpers, `main()` bootstrap. |
| `store.go` | Persistence layer: `Book` model, `Store` wrapping `*sql.DB`, CRUD methods, schema migration in `OpenStore`, `errNotFound` sentinel. |
| `main_test.go` | Integration tests exercising the full handler against an in-memory SQLite store. |

## Interfaces

- `newHandler(*Store) http.Handler` — builds the Go 1.22+ method-pattern mux
  (`GET /books/{id}`, etc.). This is the seam the tests target.
- `Store` methods: `Create`, `List(author)`, `Get(id)`, `Update`, `Delete`,
  `Close`. `List` applies the optional `?author=` filter in SQL.
- Errors flow up as `errNotFound`, mapped to HTTP 404 by `serverErr`; all other
  errors become 500 with a logged internal message.

## Flow

`request → mux route → handler → decodeBook/pathID (validation) → Store method
(SQL) → writeJSON`. Validation (title/author required, non-negative year, id > 0)
happens in the HTTP layer before touching the store. The store owns the schema and
sets `SetMaxOpenConns(1)` to keep `:memory:` DBs consistent and avoid write locks.

## Notes

- Idiomatic use of the modern stdlib routing (`PathValue`, method patterns) — no
  third-party web framework, matching the "language + framework" latitude in the spec.
- Request bodies are capped at 1 MiB via `http.MaxBytesReader`.
- Persistence is real SQLite (file-backed by default, `DB_PATH`/`ADDR` env-tunable),
  not in-memory maps.
