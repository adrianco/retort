# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` | `app.ts:29` |
| POST | /books | `Book` (201) / `{error}` (400) | `app.ts:33` |
| GET | /books | `[Book]` (200), optional `?author=` filter | `app.ts:48` |
| GET | /books/:id | `Book` (200) / `{error}` (404) | `app.ts:59` |
| PUT | /books/:id | `Book` (200) / `{error}` (400\|404) | `app.ts:70` |
| DELETE | /books/:id | empty (204) / `{error}` (404) | `app.ts:96` |

## Library API

`buildApp(db: Database.Database): express.Application` — constructs the Express app against an injected `better-sqlite3` connection (enables `:memory:` DBs in tests).

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
