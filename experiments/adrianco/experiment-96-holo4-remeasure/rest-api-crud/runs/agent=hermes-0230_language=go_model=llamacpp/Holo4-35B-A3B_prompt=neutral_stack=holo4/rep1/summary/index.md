# Architecture summary

Small, flat Go `net/http` service (`package main`, module `bookapi`), no web framework.

| File | Role |
|------|------|
| `main.go` | `Book` model, `initDB` (SQLite via `modernc.org/sqlite`, pure-Go driver), route wiring on the default ServeMux, `healthHandler`. |
| `handlers.go` | Request routing by method (`booksHandler`, `bookHandler`), CRUD handlers (`listBooks`/`createBook`/`getBook`/`updateBook`/`deleteBook`), `validateBook`, `scanBooks`, and a test-only `resetDB`. |
| `main_test.go` | `TestMain` points `dbFile` at `test_books.db`; 9 table-light handler tests driven through `httptest`. |

**Flow:** `main` → `initDB` (create `books` table) → register `/health`, `/books`, `/books/` → `ListenAndServe(:8080)`. Path `/books/{id}` is parsed by trimming the `/books/` prefix and `strconv.Atoi`. Persistence is a single file-backed SQLite DB with a global `*sql.DB`; all queries are parameterized (no SQL injection surface). JSON in/out via `encoding/json`, status codes set explicitly per branch.

**Notable:** ISBN column is `NOT NULL UNIQUE`; UNIQUE violations are mapped to HTTP 409. No pagination, no auth (not required).

*(Produced inline — the `run-summary` skill was not invoked via the Skill tool in this session; this is a hand summary of the same scope.)*
