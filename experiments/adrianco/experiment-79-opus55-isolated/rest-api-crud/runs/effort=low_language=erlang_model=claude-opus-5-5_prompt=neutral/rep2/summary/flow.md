# Flow

```mermaid
sequenceDiagram
    Client->>books_handler: POST /books {json}
    books_handler->>books_handler: read_body + json:decode
    books_handler->>books_handler: validate/1 (title/author required)
    books_handler->>books_db: create(Book) [gen_server:call]
    books_db->>esqlite3: INSERT INTO books ...
    esqlite3-->>books_db: last_insert_rowid
    books_db->>esqlite3: SELECT ... WHERE id = ?
    esqlite3-->>books_db: row
    books_db-->>books_handler: {ok, BookMap}
    books_handler-->>Client: 201 {json} + Location header
```

A `POST /books` request is read fully (with a 1 MiB cap → 413), decoded with OTP's `json` module (bad JSON → 400), then validated by `books_handler:validate/1`: `title` and `author` must be non-empty strings (trimmed), `year`/`isbn` are optional and type-checked (violations → 422 with a per-field `details` map). On success the handler calls the `books_db` gen_server, which serialises the SQLite INSERT and re-fetches the row to return the persisted book with its generated id, and replies 201 with a `Location` header. All handler work is wrapped in a try/catch that logs and returns 500 on unexpected errors. DB access is single-threaded through one gen_server, so there is no connection pooling or concurrency within the store.
