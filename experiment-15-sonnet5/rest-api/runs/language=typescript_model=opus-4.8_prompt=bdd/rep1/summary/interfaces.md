# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.ts:createApp` (health) |
| POST | /books | `201 Book` \| `400 {errors}` | `app.ts:createApp` (create) |
| GET | /books | `200 [Book]` (supports `?author=`) | `app.ts:createApp` (list) |
| GET | /books/:id | `200 Book` \| `400` \| `404` | `app.ts:createApp` (get) |
| PUT | /books/:id | `200 Book` \| `400` \| `404` | `app.ts:createApp` (update) |
| DELETE | /books/:id | `204` \| `400` \| `404` | `app.ts:createApp` (delete) |

## Library API

- `createDatabase(filename?)` → `DatabaseSync` — creates/opens a SQLite DB and applies the `books` schema.
- `createApp(db)` → `Express` — builds the app around an injected DB connection.
- `BookRepository` — `create`, `findAll(authorFilter?)`, `findById`, `update`, `delete`.
- `validateBook(body)` → `ValidationResult` — validates/normalises a book payload.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
