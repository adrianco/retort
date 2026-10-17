# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201` book + `Location` header | `server.py:_create_book` |
| GET | /books | `200` `[Book]` in id order, `?author=` filter | `server.py:_list_books` |
| GET | /books/{id} | `200` book \| `404` | `server.py:_get_book` |
| PUT | /books/{id} | `200` updated book \| `404` | `server.py:_update_book` |
| DELETE | /books/{id} | `204` \| `404` | `server.py:_delete_book` |
| GET | /health | `200 {"status":"ok"}` \| `503` | `server.py:_health` |

Error handling: `400` invalid body/validation, `413` body > 1 MiB, `415` wrong
`Content-Type`, `405` with `Allow` header for known path + wrong method, `404`
for unknown paths, `500` for unhandled exceptions (logged, not returned).

## Library API

- `store.BookStore(path)` — `create`, `get`, `list_books`, `update`, `delete`, `ping`, `close`
- `validation.validate_book(payload, *, partial=False)` → cleaned fields / raises `ValidationError`
- `server.create_server(db_path, host, port)` → `BookHTTPServer`

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
Custom `casefold()` SQL function gives Unicode-aware case-insensitive author match.
