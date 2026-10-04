# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{status:"ok"}` (after `SELECT 1`) | `app.ts:53` |
| GET | /books | 200 `[Book]`, optional `?author=` exact filter; 400 on repeated param | `app.ts:58` |
| POST | /books | 201 `Book` + `Location` header; 400 on invalid body | `app.ts:69` |
| GET | /books/:id | 200 `Book`; 404 if missing; 400 on non-positive-int id | `app.ts:87` |
| PUT | /books/:id | 200 replaced `Book`; 404 if missing; 400 on invalid body/id | `app.ts:93` |
| DELETE | /books/:id | 200 `{message:"Book deleted"}`; 404 if missing | `app.ts:106` |
| (any) | * | 404 `{error:"Route not found"}` | `app.ts:112` |

`app.param('id')` (`app.ts:79`) rejects non-positive-integer ids with 400. Error handler (`app.ts:113`) maps oversized bodies→413, bad JSON→400, bad encoding→415, else→500.

## Data schema

`books` table (`app.ts:40`): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL CHECK(trim len>0), `author` TEXT NOT NULL CHECK(trim len>0), `year` INTEGER (nullable), `isbn` TEXT (nullable). Index `books_author` on `author`. Storage via Node built-in `node:sqlite` `DatabaseSync`.

## Library API

`createApp(databasePath = 'books.sqlite')` returns `{ app, close }`. `validate(value)` returns a normalized `BookInput` or throws.
