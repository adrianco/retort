# Books API

A REST API for managing a book collection, written in Erlang/OTP using
Cowboy for HTTP and DETS for embedded persistent storage.

## Requirements

- Erlang/OTP 27 or newer (uses the built-in `json` module)
- rebar3

## Build

```
rebar3 compile
```

## Run

Interactive shell (starts the API on port 8080):

```
rebar3 shell
```

Override the port or database file via OS env or application env:

```
ERL_FLAGS="-books port 9090 -books db_file '\"/tmp/books.dets\"'" rebar3 shell
```

## Tests

```
rebar3 ct
```

## API

All endpoints accept and return JSON.

| Method | Path             | Description                                    |
|--------|------------------|------------------------------------------------|
| GET    | `/health`        | Health check; returns `{"status":"ok"}`        |
| POST   | `/books`         | Create a book (`title`, `author` required)     |
| GET    | `/books`         | List all books (optional `?author=` filter)    |
| GET    | `/books/{id}`    | Retrieve a single book                         |
| PUT    | `/books/{id}`    | Update one or more fields on a book            |
| DELETE | `/books/{id}`    | Delete a book                                  |

### Book object

```json
{
  "id": "string",
  "title": "string",
  "author": "string",
  "year": 1937,
  "isbn": "string"
}
```

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid input (missing required fields, invalid JSON)
- `404 Not Found` — unknown book id or route
- `405 Method Not Allowed` — unsupported HTTP method on a route

### Examples

```
curl -s http://localhost:8080/health

curl -s -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"Tolkien","year":1937}'

curl -s 'http://localhost:8080/books?author=Tolkien'

curl -s -X PUT http://localhost:8080/books/<id> \
  -H 'Content-Type: application/json' \
  -d '{"year":1938}'

curl -s -X DELETE http://localhost:8080/books/<id>
```

## Storage

Data is stored in a DETS file (default: `books.dets` in the working
directory). DETS is OTP's built-in disk-backed key/value store — the
Erlang-equivalent of an embedded database.
