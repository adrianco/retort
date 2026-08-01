# Books API

A dependency-free Erlang REST service backed by OTP's persistent DETS embedded database.

## Run

```sh
rebar3 compile
rebar3 shell
```

The server listens on `http://localhost:8080`; its data is saved in `books.dets`.
Set `port` and `storage_file` in the `books_api` application environment before starting if needed.

## API

- `GET /health`
- `POST /books` with JSON such as `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`
- `GET /books` and `GET /books?author=Frank+Herbert`
- `GET /books/{id}`
- `PUT /books/{id}` with the full required `title` and `author` fields
- `DELETE /books/{id}`

Responses are JSON. Creation returns 201, successful deletion returns 204, invalid input returns 400, and missing books/routes return 404.

## Test

```sh
rebar3 eunit
```
