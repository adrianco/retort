# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{status: "ok"}` | `router.ex:13` |
| POST | /books | 201 `Book` \| 400 \| 422 \| 413 | `router.ex:17` |
| GET | /books | 200 `[Book]` (optional `?author=`) | `router.ex:27` |
| GET | /books/:id | 200 `Book` \| 404 | `router.ex:39` |
| PUT | /books/:id | 200 `Book` \| 400 \| 404 \| 422 | `router.ex:48` |
| DELETE | /books/:id | 204 \| 404 | `router.ex:59` |
| (any) | /* | 404 `{error: "not found"}` | `router.ex:68` |

## Data schema

`books` table (SQLite via exqlite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL,
`author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).

## Library API

- `BookApi.Store` — GenServer CRUD over the SQLite connection.
- `BookApi.Book.validate/1` — returns `{:ok, attrs}` (atom keys) or `{:error, errors_map}`.
