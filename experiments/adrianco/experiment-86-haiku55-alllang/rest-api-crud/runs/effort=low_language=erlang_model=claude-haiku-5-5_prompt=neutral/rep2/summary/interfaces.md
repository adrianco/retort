# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status: ok}` | `books_http:init/2` (health) |
| POST | /books | `201 Book` + `Location` / `400` | `books_http:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` exact match) | `books_http:list_books` |
| GET | /books/{id} | `200 Book` \| `404` | `books_http:item_request(GET)` |
| PUT | /books/{id} | `200 Book` \| `404` / `400` | `books_http:item_request(PUT)` |
| DELETE | /books/{id} | `204` \| `404` | `books_http:item_request(DELETE)` |

Unsupported methods on a known path return `405` with an `Allow` header. A
non-numeric or non-positive `{id}` returns `404`.

## Library API (books_store)

`create/1`, `get/1`, `list/1` (author filter or `undefined`), `update/2`,
`delete/1` — all serialised through a single gen_server.

## Data schema

DETS table `books` (type `set`): key `Id :: pos_integer()` → value
`#{id, title, author, year, isbn}`. A reserved `{counter, N}` tuple holds the
monotonic id sequence (`dets:update_counter/3`), so ids survive restarts.
