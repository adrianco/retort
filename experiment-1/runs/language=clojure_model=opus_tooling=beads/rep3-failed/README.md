# Books REST API

A small Clojure REST API for managing a book collection. Uses Ring + Jetty, Compojure, next.jdbc, and SQLite.

## Requirements

- Clojure CLI (1.11+)
- Java 11+

## Run

```
clojure -M:run
```

Server listens on port `3000` by default. Override with env vars:

- `PORT` — port (default `3000`)
- `DB_PATH` — SQLite file path (default `books.db`)

## Test

```
clojure -M:test
```

## Endpoints

| Method | Path          | Description                          |
| ------ | ------------- | ------------------------------------ |
| GET    | `/health`     | Health check — returns `{"status":"ok"}` |
| POST   | `/books`      | Create a book (JSON body)            |
| GET    | `/books`      | List books, optional `?author=` filter |
| GET    | `/books/{id}` | Get one book                         |
| PUT    | `/books/{id}` | Update a book                        |
| DELETE | `/books/{id}` | Delete a book                        |

### Book schema

```json
{ "title": "Dune", "author": "Herbert", "year": 1965, "isbn": "978-0441172719" }
```

`title` and `author` are required. `year` and `isbn` are optional.

### Example

```
curl -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965}'

curl localhost:3000/books?author=Herbert
```

## Status codes

- `201` — created
- `200` — success
- `204` — deleted
- `400` — validation / bad JSON
- `404` — not found
