# Architecture Summary

Single-package Go service (`package main`, module `bookapi`) implementing a book-collection REST API over an embedded SQLite database.

## Modules / files

| File | Role |
|------|------|
| `main.go` | Everything: `Book` model, `BookStore` (SQLite data layer), HTTP handlers, and `main()` route wiring. |
| `main_test.go` | Three tests exercising the `BookStore` data layer directly. |

## Layers

- **Model** — `Book{ID,Title,Author,Year,ISBN}` with JSON tags (`main.go:15`).
- **Data layer** — `BookStore` wraps `*sql.DB`; `NewBookStore` opens the DB and creates the `books` table (`main.go:27`). CRUD methods: `CreateBook`, `GetAllBooks(authorFilter)`, `GetBookByID`, `UpdateBook`, `DeleteBook`.
- **HTTP layer** — stdlib `net/http` with `http.HandleFunc`. `/books` (POST/GET), `/books/` (GET/PUT/DELETE by trailing-int id), `/health`. Handlers are free functions taking `*BookStore` (`main.go:168`+).

## Request flow

`main()` opens `./books.db`, registers three route patterns, and serves on `:8080`. `/books/` handler parses the id via `strconv.Atoi` on the path suffix, then dispatches by method.

## Notable design points

- Persistence is real SQLite (`github.com/mattn/go-sqlite3`), not in-memory.
- No router library; path/id parsing is manual string trimming.
- Not-found handling for update/delete relies on string-matching `sql.ErrNoRows`, which never fires for `Exec` — see findings.
- Tests bypass the HTTP layer entirely (data layer only), leaving handlers/validation/status-codes uncovered (coverage 32.5%).
