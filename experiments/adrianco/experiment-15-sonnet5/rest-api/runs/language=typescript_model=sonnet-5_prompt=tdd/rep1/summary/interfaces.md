# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.ts:/health` |
| POST | /books | `201 Book \| 400` | `app.ts:/books` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.ts:/books` |
| GET | /books/:id | `200 Book \| 404` | `app.ts:/books/:id` |
| PUT | /books/:id | `200 Book \| 400 \| 404` | `app.ts:/books/:id` |
| DELETE | /books/:id | `204 \| 404` | `app.ts:/books/:id` |

## Data schema

`books` table: id (INTEGER, pk, autoincrement), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).

## Library API

- `createDb(path: string): DatabaseSync` — opens `node:sqlite` DB, creates table.
- `createApp(db: DatabaseSync): Express` — builds the Express app.
