# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | `/health` | `200 {"status":"healthy"}` | `main.go:53 healthHandler` |
| POST | `/books` | `201 Book` \| `400` \| `500` | `main.go:72 createBookHandler` |
| GET | `/books` (`?author=`) | `200 [Book]` (`null` when empty) \| `500` | `main.go:113 getBooksHandler` |
| GET | `/books/{id}` | `200 Book` \| `400` \| `404` \| `500` | `main.go:155 getBookHandler` |
| PUT | `/books/{id}` | `200 Book` \| `400` \| `404` \| `500` | `main.go:186 updateBookHandler` |
| DELETE | `/books/{id}` | `204` \| `400` \| `404` \| `500` | `main.go:241 deleteBookHandler` |

Routing is `net/http` `ServeMux` with two patterns: `/books` (method-switched in `booksHandler`, `main.go:60`) and the `/books/` subtree (method-switched inline in `main()`, `main.go:288`). IDs are parsed by `strings.TrimPrefix` + `strconv.Atoi`.

## CLI commands

(none) — single binary; `PORT` env var selects the listen port (`main.go:311`), default `8080`.

## Library API

(none exported) — `package main`; all symbols are package-private and exercised directly by `main_test.go`.

## Data schema

`books` table (`main.go:37`), SQLite file `./books.db`:

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| year | INTEGER | |
| isbn | TEXT | |

JSON shape: `{"id","title","author","year","isbn"}` (`Book`, `main.go:17`).
