# Book Collection API

A Rust REST service for creating and managing books. Data is stored in SQLite.

## Run

```sh
cargo run
```

The service listens at `http://127.0.0.1:3000` and creates `books.db` in the working directory. Set `DATABASE_URL` to use a different SQLite database path.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Returns `ok` when the service is running |
| POST | `/books` | Create a book |
| GET | `/books?author=Name` | List books, optionally filtered by exact author |
| GET | `/books/{id}` | Fetch one book |
| PUT | `/books/{id}` | Replace a book |
| DELETE | `/books/{id}` | Delete a book |

Book request bodies use JSON, for example:

```json
{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}
```

`title` and `author` are required and cannot be blank. Successful creation returns `201`, deletion returns `204`, missing books return `404`, and invalid input returns `400`.

## Test

```sh
cargo test
```
