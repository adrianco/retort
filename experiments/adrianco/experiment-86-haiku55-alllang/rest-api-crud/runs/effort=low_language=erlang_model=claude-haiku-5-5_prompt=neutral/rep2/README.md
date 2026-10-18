# Books API

A REST API for managing a book collection, written in Erlang/OTP.
HTTP is served by [Cowboy](https://ninenines.eu/), JSON uses the built-in `json` module (OTP 27+),
and books are persisted to a DETS file (OTP's built-in disk-backed table store).

## Requirements

- Erlang/OTP 27 or newer (tested with OTP 29)
- [rebar3](https://rebar3.org/)

## Setup

```sh
rebar3 compile
```

## Run

```sh
rebar3 shell
```

The API listens on port **8080** and stores data in `books.dets` in the working directory.
Both can be changed in `src/books.app.src` (`port`, `db_file`).

Quick check:

```sh
curl -i http://localhost:8080/health
```

## Test

```sh
rebar3 eunit
```

The suite contains unit tests for validation and storage, and end-to-end HTTP tests that start
the application on an ephemeral port.

## Endpoints

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| POST   | `/books`      | Create a book                                | 201     |
| GET    | `/books`      | List books; optional `?author=` exact match  | 200     |
| GET    | `/books/{id}` | Get one book                                 | 200     |
| PUT    | `/books/{id}` | Replace a book's fields                      | 200     |
| DELETE | `/books/{id}` | Delete a book                                | 204     |
| GET    | `/health`     | Health check                                 | 200     |

### Book fields

| Field    | Type    | Required | Notes                                        |
|----------|---------|----------|----------------------------------------------|
| `title`  | string  | yes      | Non-blank; surrounding whitespace is trimmed |
| `author` | string  | yes      | Non-blank; surrounding whitespace is trimmed |
| `year`   | integer | no       | 0–9999                                       |
| `isbn`   | string  | no       | 10–17 characters: digits, `-`, or `X`        |

`id` is assigned by the server. `PUT` takes the full set of fields; omitted optional fields are reset to `null`.

### Examples

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl http://localhost:8080/books?author=Frank%20Herbert

curl -X PUT http://localhost:8080/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl -X DELETE http://localhost:8080/books/1
```

### Errors

Errors return a JSON body of the form `{"error": "..."}`. Validation failures return `400`
with a `details` array listing every problem:

```json
{"error": "validation failed", "details": ["title is required"]}
```

| Status | Cause                                        |
|--------|----------------------------------------------|
| 400    | Invalid JSON or failed validation            |
| 404    | Book not found, or a non-numeric/zero id     |
| 405    | Method not supported on that path (`Allow` header set) |
