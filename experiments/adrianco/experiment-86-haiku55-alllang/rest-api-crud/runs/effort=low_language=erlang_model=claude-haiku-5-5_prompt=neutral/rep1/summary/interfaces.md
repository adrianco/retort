# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `books_health_handler:init/2` |
| GET | /books | `[Book]` 200 | `books_collection_handler:list/1` |
| GET | /books?author= | `[Book]` 200 (NOCASE exact match) | `books_collection_handler:list/1` |
| POST | /books | `Book` 201 / 400 | `books_collection_handler:create/1` |
| GET | /books/{id} | `Book` 200 / 404 | `books_item_handler:dispatch/3` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 | `books_item_handler:dispatch/3` |
| DELETE | /books/{id} | 204 / 404 | `books_item_handler:dispatch/3` |

Unmatched methods return 405 with an `allow` header; unknown routes and non-positive-integer ids return 404.

## Data schema

`books` table (SQLite via esqlite3): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).

## Library API

`books_validate:validate/1` → `{ok, #{title,author,year,isbn}} | {error, [binary()]}`. `books_db` exposes the CRUD gen_server client API.
