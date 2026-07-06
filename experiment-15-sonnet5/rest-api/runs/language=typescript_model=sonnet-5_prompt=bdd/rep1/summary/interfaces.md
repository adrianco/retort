# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.ts:10` |
| POST | /books | `201 Book` / `400 {errors}` | `app.ts:14` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.ts:37` |
| GET | /books/:id | `200 Book` / `400` / `404 {errors}` | `app.ts:50` |
| PUT | /books/:id | `200 Book` / `400` / `404 {errors}` | `app.ts:63` |
| DELETE | /books/:id | `204` / `400` / `404 {errors}` | `app.ts:99` |

## Data schema

`books` table (SQLite via `node:sqlite`):
id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER, nullable), isbn (TEXT, nullable).

## Library API

- `createApp(db: DatabaseSync): Express` — app factory (dependency-injects the DB, enabling in-memory test DBs)
- `createDatabase(filename: string): DatabaseSync` — opens/creates the SQLite DB and ensures schema
- `validateBookInput(input, {partial?}): ValidationResult` — full or partial (PUT) validation
