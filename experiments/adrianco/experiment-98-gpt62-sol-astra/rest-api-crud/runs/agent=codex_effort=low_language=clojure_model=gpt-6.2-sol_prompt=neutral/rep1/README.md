# Book Collection API

A Clojure REST API using Ring, Jetty, and SQLite.

## Setup and run

Install Java 11 or later and Leiningen. From this directory, run:

```sh
lein run
```

The server listens at `http://localhost:3000` and creates `books.sqlite` on startup. Set `PORT` to change the port or `BOOK_DB_PATH` to use a different SQLite file. The file's parent directory must exist and be writable.

## API

| Method | Path | Successful response |
| --- | --- | --- |
| POST | `/books` | `201` with the created book and a `Location` header |
| GET | `/books` | `200` with an array ordered by ID |
| GET | `/books/{id}` | `200` with the book |
| PUT | `/books/{id}` | `200` with the replacement book |
| DELETE | `/books/{id}` | `204` with an empty body |
| GET | `/health` | `200` with `{"status":"ok"}` |

POST and PUT accept JSON objects. Both require nonblank string values for `title` and `author`. The optional `year` is an integer and the optional `isbn` is a string. PUT replaces all editable fields, so omitted optional fields become null. Invalid input returns `400`, and missing books return `404`. Error responses contain an `error` field.

Add `?author=<author>` to the collection URL to filter by exact, case-sensitive author name.

```sh
curl -i http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}'

curl -G http://localhost:3000/books --data-urlencode 'author=Octavia E. Butler'
```

## Test and build

```sh
lein test
lein uberjar
```

The tests use temporary SQLite files. Run the packaged service with `java -jar target/book-api-0.1.0-standalone.jar`.
