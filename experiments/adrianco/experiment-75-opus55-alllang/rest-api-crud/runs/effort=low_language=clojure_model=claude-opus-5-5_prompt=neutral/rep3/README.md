# Books REST API (Clojure)

Ring + Compojure + next.jdbc + SQLite.

## Requirements
- Java 11+ and the Clojure CLI (`clojure`)

## Run
```
clojure -M:run          # PORT (default 3000), DB_PATH (default books.db)
```

## Test
```
clojure -M:test
```

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | JSON `{title, author, year?, isbn?}` → 201; 400 on validation errors |
| GET | /books | `?author=` exact-match filter |
| GET | /books/{id} | 404 if missing |
| PUT | /books/{id} | full replace, same validation → 200 |
| DELETE | /books/{id} | 204, or 404 |

Example:
```
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```
