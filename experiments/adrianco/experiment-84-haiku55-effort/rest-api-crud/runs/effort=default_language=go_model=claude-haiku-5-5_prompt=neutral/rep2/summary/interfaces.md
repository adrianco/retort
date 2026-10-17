# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 503` | `server.go:health` |
| POST | /books | `Book` (201) \| 400 | `server.go:createBook` |
| GET | /books | `[Book]` (200), `?author=` filter | `server.go:listBooks` |
| GET | /books/{id} | `Book \| 400 \| 404` | `server.go:getBook` |
| PUT | /books/{id} | `Book \| 400 \| 404` | `server.go:updateBook` |
| DELETE | /books/{id} | `204 \| 400 \| 404` | `server.go:deleteBook` |

Unmatched routes/methods are rewritten to JSON `{"error": ...}` (404/405) by `jsonErrors`.

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null),
year (INTEGER default 0), isbn (TEXT default ''). Index `idx_books_author` on author COLLATE NOCASE.

## Exported library API

`OpenStore(path) (*Store, error)`, `Store.{Create,Get,List,Update,Delete,Ping,Close}`,
`NewServer(store).Handler() http.Handler`, `BookInput.Validate() map[string]string`.
