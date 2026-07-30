# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status,database,books,version}` / `503` | `routes.py:health` |
| GET | / | `200 {name,version,endpoints}` | `routes.py:index` |
| GET | /openapi.json | `200 {openapi spec}` | `routes.py:openapi` |
| GET | /books | `200 [Book]` (+ `X-Total-Count`) | `routes.py:list_books` |
| POST | /books | `201 Book` (+ `Location`) | `routes.py:create_book` |
| GET | /books/{id} | `200 Book \| 404` | `routes.py:get_book` |
| PUT | /books/{id} | `200 Book \| 404` (full replace) | `routes.py:replace_book` |
| PATCH | /books/{id} | `200 Book \| 404` (partial) | `routes.py:patch_book` |
| DELETE | /books/{id} | `204 \| 404` | `routes.py:delete_book` |

`GET /books` query params: `author` (exact, case-insensitive), `title` (substring), `year`, `sort` (id/title/author/year/created_at/updated_at, `-` prefix for desc), `limit`, `offset`.

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, NOT NULL, non-blank CHECK), `author` (text, NOT NULL, non-blank CHECK), `year` (int, nullable), `isbn` (text, nullable), `created_at` (text), `updated_at` (text). Indexes on author, title, year.

## Error shape

`{"error": <message>, "code": <machine_code>}`, plus `details` (field→reason) on validation failures.
