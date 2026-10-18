# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201 Book` / `400 {error}` | `api.c:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `api.c:list_books` |
| GET | /books/{id} | `200 Book` / `404 {error}` | `api.c:get_book` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `api.c:update_book` |
| DELETE | /books/{id} | `204` (no body) / `404 {error}` | `api.c:delete_book` |
| GET | /health | `200 {"status":"ok"}` | `api.c:api_handle` |

All responses are `Content-Type: application/json` except `204`. Unknown
methods on a known path return `405`; unknown paths return `404`. HTTP-level
errors are also emitted: `413` (body too large), `431` (headers too large),
`400` (malformed request line / headers / chunked encoding).

## Data schema

`books` table (SQLite):

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| year | INTEGER | nullable |
| isbn | TEXT | nullable |

Index `idx_books_author` on `author COLLATE NOCASE` backs the case-insensitive
author filter.

## Library API (internal)

- **db.h** — `Store` handle + `store_*` CRUD returning status codes (1 found /
  0 not-found / -1 error); `BookFields` (input) and `Book` (output) structs.
- **json.h** — `json_parse_object` (strict parser, rejects trailing bytes,
  control chars, lone surrogates, `\u0000`, leading-zero numbers), `json_get`
  (last-duplicate-key wins), `json_write_string` (escaping serializer).
- **http.h** — `RequestHead` struct; `http_parse_head`, `query_param`,
  `http_listen`, `http_serve(max_connections)` (bounded loop enables testing).
- **strbuf.h** / **util.h** — growable buffer and allocation/hex helpers.

## CLI commands

(none — the binary takes no arguments; configured via `PORT` / `DB_PATH` env vars.)
