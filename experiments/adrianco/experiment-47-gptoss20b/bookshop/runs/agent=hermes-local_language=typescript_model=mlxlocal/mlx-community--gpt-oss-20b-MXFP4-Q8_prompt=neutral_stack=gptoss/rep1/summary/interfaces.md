# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:'ok'}` | `index.ts:19` |
| POST | /books | `201 Book \| 400` | `index.ts:24` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `index.ts:42` |
| GET | /books/:id | `200 Book \| 404` | `index.ts:56` |
| PUT | /books/:id | `200 Book \| 400 \| 404` | `index.ts:67` |
| DELETE | /books/:id | `204 \| 404` | `index.ts:91` |

## Data schema

`books` table: id (INTEGER, pk autoincrement), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).

## Library API

`getDb(dbPath = './books.db')` — opens the SQLite file via the `sqlite`/`sqlite3` wrapper, runs the `CREATE TABLE IF NOT EXISTS` migration, returns the open DB handle.
