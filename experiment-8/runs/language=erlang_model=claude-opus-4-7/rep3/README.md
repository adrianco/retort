# Book Collection REST API (Erlang / Cowboy)

A small REST service for managing a book collection. Written in Erlang using
[Cowboy](https://github.com/ninenines/cowboy) for HTTP, [jsone](https://github.com/sile/jsone)
for JSON, and DETS (Erlang's built-in embedded disk store) for persistence.

## Requirements

- Erlang/OTP 23 or newer
- [`rebar3`](https://rebar3.org/)

This project was built and tested with Erlang/OTP 29 and rebar3 3.27.

## Running

```bash
rebar3 compile
rebar3 shell
```

The server listens on port `8080` by default (configurable via the
`book_api`/`port` application environment).

Data is persisted to a DETS file named `books.dets` in the current working
directory (configurable via `book_api`/`db_file`).

## API

| Method | Path              | Description                                |
|--------|-------------------|--------------------------------------------|
| GET    | `/health`         | Health check: `{"status":"ok"}`            |
| GET    | `/books`          | List all books. `?author=<name>` filters.  |
| POST   | `/books`          | Create a book.                             |
| GET    | `/books/{id}`     | Fetch a single book by id.                 |
| PUT    | `/books/{id}`     | Update a book.                             |
| DELETE | `/books/{id}`     | Delete a book.                             |

### Book schema

```json
{
  "id": 1,
  "title": "Programming Erlang",
  "author": "Joe Armstrong",
  "year": 2007,
  "isbn": "978-1937785536"
}
```

`title` and `author` are required for `POST` and `PUT`. `year` and `isbn` are
optional.

### Examples

```bash
# health
curl -s http://localhost:8080/health

# create
curl -s -X POST http://localhost:8080/books \
     -H 'content-type: application/json' \
     -d '{"title":"Programming Erlang","author":"Joe Armstrong","year":2007,"isbn":"978-1937785536"}'

# list
curl -s http://localhost:8080/books

# list filtered
curl -s 'http://localhost:8080/books?author=Joe%20Armstrong'

# get one
curl -s http://localhost:8080/books/1

# update
curl -s -X PUT http://localhost:8080/books/1 \
     -H 'content-type: application/json' \
     -d '{"title":"Programming Erlang, 2e","author":"Joe Armstrong","year":2013}'

# delete
curl -s -X DELETE http://localhost:8080/books/1 -o /dev/null -w '%{http_code}\n'
```

### Status codes

| Code | Meaning                                  |
|------|------------------------------------------|
| 200  | OK (GET, PUT)                            |
| 201  | Created (POST)                           |
| 204  | No Content (DELETE)                      |
| 400  | Bad Request — invalid JSON or validation |
| 404  | Not Found                                |
| 405  | Method Not Allowed                       |

## Tests

```bash
rebar3 eunit
```

The test suite (`test/book_api_tests.erl`) boots the application on port 8089
with its own DETS file and exercises the API end-to-end via `httpc`:

- health endpoint returns `{"status":"ok"}`
- POST + GET round-trips a book
- `?author=` filters the list
- POST without `title` or `author` returns 400
- PUT updates an existing book
- DELETE removes a book (subsequent GET returns 404)
- GET on an unknown id returns 404
