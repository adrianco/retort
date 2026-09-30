# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} 200/503` | `handlers.go:health` |
| GET | /books | `[Book] 200` (optional `?author=` filter) | `handlers.go:listBooks` |
| POST | /books | `Book 201` (+ `Location` header) | `handlers.go:createBook` |
| GET | /books/{id} | `Book 200 \| 404` | `handlers.go:getBook` |
| PUT | /books/{id} | `Book 200 \| 404` | `handlers.go:updateBook` |
| DELETE | /books/{id} | `204 \| 404` | `handlers.go:deleteBook` |

Method-less fallbacks return JSON `405` with an `Allow` header; unknown paths return JSON `404`. All error bodies are `{"error":..., "details":{...}}`.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, CHECK non-blank), `author` (TEXT NOT NULL, CHECK non-blank), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Index `books_author_idx` on `author COLLATE NOCASE`.

## Domain model

`book.Input{Title, Author string; Year *int; ISBN *string}`; `book.Book{ID int64; Input}`. Validation: title/author required, ≤500 chars, no control chars; year 0–9999; ISBN ≤32 chars.

## Config

Flags `-addr`, `-db`; env `PORT`, `DB_PATH`. Precedence: defaults < env < flags.
