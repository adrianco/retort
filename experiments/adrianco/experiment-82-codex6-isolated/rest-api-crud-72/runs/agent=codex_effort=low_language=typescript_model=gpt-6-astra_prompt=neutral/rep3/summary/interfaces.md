# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` (after a `SELECT 1` DB check) | `app.ts:41` |
| GET | /books | `200 [Book]` (ordered by id; `?author=` exact filter) | `app.ts:45` |
| POST | /books | `201 Book` + `Location` header, or `400` | `app.ts:56` |
| GET | /books/:id | `200 Book` \| `404` \| `400` (bad id) | `app.ts:71` |
| PUT | /books/:id | `200 Book` (full replace) \| `404` \| `400` | `app.ts:76` |
| DELETE | /books/:id | `200 {message}` \| `404` \| `400` | `app.ts:88` |
| * (unmatched) | any | `404 {error:"Route not found"}` | `app.ts:93` |

Error envelope: `{"error": "message"}`. Codes: 400 invalid input/id, 404 missing book/route, 413 body >100 KB, 500 unexpected.

## Library API

`createApp(databasePath = 'books.sqlite')` → `{ app, close }` — an Express instance plus a DB-close handle. `Book` interface exported.

## Data schema

`books` table (SQLite via `node:sqlite`): `id INTEGER PK AUTOINCREMENT`, `title TEXT NOT NULL CHECK(trim>0)`, `author TEXT NOT NULL CHECK(trim>0)`, `year INTEGER NULL`, `isbn TEXT NULL`. Access uses parameterized prepared statements.
