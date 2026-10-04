# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` (200) | `core.clj:app` |
| GET | /books | `[Book]` (200), optional `?author=` exact filter | `core.clj:app` → `db/list-books` |
| POST | /books | `Book` (201) / `400` validation | `core.clj:app` → `db/create-book!` |
| GET | /books/{id} | `Book` (200) / `404` | `core.clj:app` → `db/get-book` |
| PUT | /books/{id} | `Book` (200) / `400` / `404` | `core.clj:app` → `db/update-book!` |
| DELETE | /books/{id} | `204` / `404` | `core.clj:app` → `db/delete-book!` |

## Data schema

`books` table (SQLite): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL),
author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).

## Library API

`books.db` exposes `datasource`, `init!`, and CRUD functions taking a datasource.
`books.core/app` builds the Ring handler from a datasource; `-main` reads `PORT`
and `DB_PATH` env vars and starts Jetty.
