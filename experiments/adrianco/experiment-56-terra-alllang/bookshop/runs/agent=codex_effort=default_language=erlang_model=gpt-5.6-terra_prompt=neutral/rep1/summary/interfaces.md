# Interfaces

## HTTP routes (`books_http:route/4`)

| Method | Path | Description | Success | Errors |
|--------|------|-------------|---------|--------|
| GET | `/health` | Health check | 200 `{"status":"ok"}` | — |
| POST | `/books` | Create a book (title, author req.) | 201 book JSON | 400 invalid JSON / missing fields |
| GET | `/books` | List all; `?author=` filter | 200 array | — |
| GET | `/books/{id}` | Fetch by id | 200 book JSON | 400 bad id, 404 not found |
| PUT | `/books/{id}` | Update (title+author required) | 200 book JSON | 400, 404 not found |
| DELETE | `/books/{id}` | Delete by id | 204 no content | 400 bad id, 404 not found |
| * | (any other) | Fallthrough | — | 404 |

## Data schema

Book map (stored in DETS as `{Id::integer, Book::map}`):

```
#{id => integer, title => binary, author => binary,
  year => integer | absent, isbn => binary | absent}
```

JSON encoding emits `id, title, author, year, isbn`, with `year`/`isbn` rendered
as `null` when absent.

## Configuration (application env `books_api`)

- `port` (default `8080`) — TCP listen port
- `storage_file` (default `"books.dets"`) — DETS file path
