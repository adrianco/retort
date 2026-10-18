# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201` + book \| `400` \| `422` | `BookAPI.m:createBookWithBody:` |
| GET | /books | `200` + `[book]` (optional `?author=` exact-match filter) | `BookAPI.m:listBooksWithQuery:` |
| GET | /books/{id} | `200` + book \| `404` | `BookAPI.m:getBookWithID:` |
| PUT | /books/{id} | `200` + book \| `400` \| `422` \| `404` | `BookAPI.m:updateBookWithID:body:` |
| DELETE | /books/{id} | `204` \| `404` | `BookAPI.m:deleteBookWithID:` |
| GET | /health | `200` `{"status":"ok"}` | `BookAPI.m:handleMethod:...` |

Other codes: `405` for unsupported method on a known route; `413` when headers > 16 KB or body > 1 MB; `500` on DB error. Error bodies are `{"error": "..."}`, with a `details` array on `422`.

## Data schema

`books` table (SQLite): `id INTEGER PK AUTOINCREMENT`, `title TEXT NOT NULL`, `author TEXT NOT NULL`, `year INTEGER`, `isbn TEXT`.

## Library API

`APIResponse` value object (`statusCode`, `jsonBody`). `BookStore` CRUD methods returning `NSDictionary`/`NSArray` book rows. `BookAPI` is socket-free so it can be unit-tested directly; `HTTPServer` adapts sockets to it.
