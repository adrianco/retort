# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{status:ok}` / 503 | `BooksAPI.m:handleMethod:` |
| POST | /books | 201 + book / 400 / 422 | `BooksAPI.m:handleMethod:` → `BookStore createBook` |
| GET | /books | 200 + `[book]` (optional `?author=` filter) | `BooksAPI.m` → `BookStore booksFilteredByAuthor:` |
| GET | /books/{id} | 200 + book / 404 | `BooksAPI.m` → `BookStore bookWithID:` |
| PUT | /books/{id} | 200 + book / 400 / 422 / 404 | `BooksAPI.m` → `BookStore updateBookWithID:` |
| DELETE | /books/{id} | 204 / 404 | `BooksAPI.m` → `BookStore deleteBookWithID:` |
| (other) | /books, /books/{id} | 405 Method Not Allowed | `BooksAPI.m:handleMethod:` |

## Library API

`BookStore` — CRUD over SQLite, returns books as `NSDictionary` (id, title, author, year, isbn).
`BooksAPI` — `-handleMethod:target:body:` → `APIResponse` (status + JSON body); fully testable without sockets.
`HTTPServer` — binds a socket (ephemeral port supported), parses HTTP/1.1, delegates to `BooksAPI`.

## Data schema

`books` table: `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).
