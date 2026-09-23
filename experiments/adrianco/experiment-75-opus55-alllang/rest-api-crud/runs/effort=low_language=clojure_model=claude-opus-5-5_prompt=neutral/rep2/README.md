# Books API (Clojure)

REST service for a book collection: Ring + Jetty, Compojure, next.jdbc, SQLite.

## Requirements
Java 11+ and the Clojure CLI.

## Run
    clojure -M:run            # port 3000, db file books.db
    PORT=8080 DB_PATH=/tmp/b.db clojure -M:run

## Test
    clojure -M:test

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | JSON `{title, author, year?, isbn?}` → 201; 400 if title/author missing |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 200 or 404 |
| PUT | /books/{id} | full replace, same validation → 200 / 400 / 404 |
| DELETE | /books/{id} | 204 or 404 |

Example:
    curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
      -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
