# Book collection API

The service uses Erlang/OTP's `inets` HTTP server and stores books on disk in a DETS database.

## Build and run

Install Erlang/OTP 27 or later with Inets and EUnit, plus Make. From this directory:

```sh
make
make run
```

The default port is `8080`, and the default database file is `books.dets` in the working directory. Set `PORT` and `BOOKS_DB` to override them. The database file is created automatically. Use one running service per database file.

```sh
PORT=9000 BOOKS_DB=collection.dets make run
```

## Endpoints

| Method and path | Behavior | Success |
| --- | --- | --- |
| `GET /health` | Returns `{"status":"ok"}` when the service responds | 200 |
| `POST /books` | Creates a book and returns it with its generated integer ID and a `Location` header | 201 |
| `GET /books` | Returns an array ordered by ID. The optional `author` query parameter matches the full author name exactly, including case. | 200 |
| `GET /books/{id}` | Returns the book with the given ID | 200 |
| `PUT /books/{id}` | Replaces an existing book's fields and returns the updated book | 200 |
| `DELETE /books/{id}` | Deletes the book and returns an empty body | 204 |

POST and PUT accept JSON objects. Both require nonblank string values for `title` and `author`. The optional `year` must be an integer or null, and the optional `isbn` must be a string or null. Omitted optional fields become null. Invalid book data returns 400, and a missing book returns 404. API errors include an `error` message in a JSON object.

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'

curl 'http://localhost:8080/books?author=Octavia%20Butler'
```

## Tests

Run `make test` to exercise the HTTP request callback with temporary DETS databases. The tests cover health, CRUD, author filtering, input validation, and persistence across service restarts. Run `make test-http` to exercise the same cases over loopback HTTP.
