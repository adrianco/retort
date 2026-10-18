# Books API

A REST API for managing a book collection, written in Erlang/OTP. It uses only
the OTP standard library: a small HTTP/1.1 server on `gen_tcp`, DETS (OTP's
embedded disk-based store) for persistence, and the built-in `json` module.
There are no external dependencies.

## Requirements

- Erlang/OTP 27 or newer (uses the built-in `json` module; tested on OTP 29)
- [rebar3](https://rebar3.org)

## Setup

```sh
git clone <repo-url> books_api
cd books_api
rebar3 compile
```

## Run

```sh
rebar3 shell
```

The service listens on port `8080` by default and stores data in `books.dets`
in the working directory. Override the port with the `PORT` environment
variable:

```sh
PORT=9000 rebar3 shell
```

Settings live in `src/books_api.app.src` (`http_port`, `db_file`).

## API

Every response is `application/json`. Errors have the form `{"error": "..."}`.

| Method   | Path           | Description                              | Success |
|----------|----------------|------------------------------------------|---------|
| `POST`   | `/books`       | Create a book                            | `201`   |
| `GET`    | `/books`       | List all books; `?author=` filters       | `200`   |
| `GET`    | `/books/{id}`  | Get one book                             | `200`   |
| `PUT`    | `/books/{id}`  | Update any subset of fields              | `200`   |
| `DELETE` | `/books/{id}`  | Delete a book                            | `204`   |
| `GET`    | `/health`      | Health check                             | `200`   |

### Book fields

| Field    | Type    | Notes                                     |
|----------|---------|-------------------------------------------|
| `id`     | integer | Assigned by the server; read-only         |
| `title`  | string  | **Required** on create; must not be blank |
| `author` | string  | **Required** on create; must not be blank |
| `year`   | integer | Optional; non-negative                    |
| `isbn`   | string  | Optional                                  |

Optional fields that are not supplied are returned as `null`.

`author` filtering on `GET /books` is case-insensitive and exact, for example
`GET /books?author=frank%20herbert`.

### Examples

```sh
# Create
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List, filtered by author
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Get
curl http://localhost:8080/books/1

# Update (only the provided fields change)
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' -d '{"year":1966}'

# Delete
curl -i -X DELETE http://localhost:8080/books/1

# Health
curl http://localhost:8080/health
```

### Validation and status codes

- `400` for invalid JSON, a body that is not a JSON object, a missing or blank
  `title`/`author` on create, a wrong type for any field, or a non-integer id.
  Validation failures include a `details` array.
- `404` for an unknown book id or an unknown route.
- `405` for a known path with an unsupported method.

## Tests

```sh
rebar3 eunit
```

The tests in `test/books_api_tests.erl` start a real store and HTTP listener on
an ephemeral port for each case and call them over the network. They cover
create/fetch, validation, malformed JSON, listing and the author filter, update,
delete, and routing errors.

## Layout

```
src/
  books_api_app.erl    application callback
  books_api_sup.erl    supervisor (store + HTTP listener)
  books_store.erl      DETS-backed storage, serialised through a gen_server
  books_handler.erl    routing, validation, JSON request handling
  books_http.erl       HTTP/1.1 listener on gen_tcp
test/
  books_api_tests.erl  integration tests
```
