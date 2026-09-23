# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` \| `503` | `api.cpp:Api::handle` |
| POST | /books | `201 Book` \| `400 {error}` | `api.cpp:Api::handle` |
| GET | /books | `200 [Book]` | `api.cpp:Api::handle` |
| GET | /books?author=Name | `200 [Book]` (exact-match filter) | `api.cpp:Api::handle` |
| GET | /books/{id} | `200 Book` \| `404` | `api.cpp:Api::handle` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `api.cpp:Api::handle` |
| DELETE | /books/{id} | `204` \| `404` | `api.cpp:Api::handle` |

Unmatched methods on known paths return `405`; unknown paths return `404`.

## Library API

- `BookStore(path)` — opens/creates SQLite DB (`:memory:` supported); `create`, `list(author?)`, `get(id)`, `update`, `remove`, `healthy`.
- `Api(store).handle(Request) -> Response` — transport-independent router (tested directly, no socket needed).
- `json::parse_object(text)` / `json::escape(str)` — flat-object JSON.

## Data schema

`books` table: `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT NOT NULL DEFAULT ''.

Book JSON: `{"id":int,"title":str,"author":str,"year":int|null,"isbn":str}`.
