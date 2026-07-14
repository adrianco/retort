# Books REST API

A small Clojure REST service for managing a book collection, backed by SQLite.

## Stack

- Clojure (deps.edn / CLI)
- Ring + Jetty
- Compojure for routing
- next.jdbc + org.xerial sqlite-jdbc
- Cheshire for JSON

## Setup

Requires Clojure CLI (`clojure`) and a JDK.

## Run

```
clojure -M:run
```

The server listens on port `3000` by default (override with `PORT`). The SQLite database file is `books.db` in the working directory and is created on first launch.

## Test

```
clojure -M:test
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET    | /health | Health check |
| POST   | /books  | Create a book (JSON: `title`, `author`, `year`, `isbn`) |
| GET    | /books  | List books; optional `?author=` filter |
| GET    | /books/{id} | Fetch a single book |
| PUT    | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

`title` and `author` are required on create and update; omissions return HTTP 400. Unknown IDs return 404. Successful create returns 201; delete returns 204.

### Example

```
curl -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"978-0441172719"}'
```
