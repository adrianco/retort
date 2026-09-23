# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `books_api:handle/4` |
| POST | /books | `201 Book` \| `400` | `books_api:collection/3` → `books_store:create/1` |
| GET | /books | `200 [Book]` | `books_api:collection/3` → `books_store:list/1` |
| GET | /books?author=Name | `200 [Book]` (exact author match) | `books_api:collection/3` → `books_store:list/1` |
| GET | /books/{id} | `200 Book` \| `404` | `books_api:item/3` → `books_store:get/1` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `books_api:item/3` → `books_store:update/2` |
| DELETE | /books/{id} | `204` \| `404` | `books_api:item/3` → `books_store:delete/1` |

Unmatched method on a known path returns `405`; unhandled exceptions return `500`.

## Library API

- `books_api:validate/1` — returns `{ok, NormalisedBook}` or `{error, [Message]}`. Requires non-blank `title` and `author`; optional `year` (integer) and `isbn` (string).
- `books_store` gen_server — `create/1`, `list/1`, `get/1`, `update/2`, `delete/1`.

## Data schema

DETS table `books_dets` (type `set`): key = integer `id`, value = book map with keys `id`, `title`, `author`, `year` (int|null), `isbn` (str|null). Auto-increment id derived from the current max key at init.
