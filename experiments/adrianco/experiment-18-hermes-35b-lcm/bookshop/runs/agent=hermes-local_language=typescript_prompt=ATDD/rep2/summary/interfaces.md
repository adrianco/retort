# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.ts:27` |
| POST | /books | `201 Book` / `400 {error}` | `app.ts:32` |
| GET | /books | `200 {books:[Book]}` (optional `?author=`) | `app.ts:43` |
| GET | /books/:id | `200 Book` / `404 {error}` | `app.ts:51` |
| PUT | /books/:id | `200 Book` / `400` / `404` | `app.ts:61` |
| DELETE | /books/:id | `200 {message}` / `404 {error}` | `app.ts:76` |

## Data schema

`books` table (`db.ts:19`): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER, nullable), isbn (TEXT, nullable). SQLite via better-sqlite3, `journal_mode = WAL`.

## Library API

Exported from `db.ts`: `createDb`, `createBook`, `getAllBooks`, `getBook`, `updateBook`, `deleteBook`, `clearAll`, `COUNT_ALL`, `COUNT_BY_AUTHOR`, `setAppDb`/`getAppDb`/`shutdownDb` (module-global handle). Exported from `validation.ts`: `validateBook`.
