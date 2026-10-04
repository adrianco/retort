# Flow

```mermaid
sequenceDiagram
    Client->>book_api_books_handler: POST /books {json}
    book_api_books_handler->>book_api_books_handler: read_body + json:decode
    book_api_books_handler->>book_api_books_handler: validate/1 (title, author required)
    book_api_books_handler->>book_store: create(Fields)
    book_store->>book_store: next_id() via dets:update_counter
    book_store->>book_store: dets:insert + dets:sync
    book_store-->>book_api_books_handler: Book (with id)
    book_api_books_handler-->>Client: 201 {json} + Location header
```

A `POST /books` reads the body (capped at 1 MB), decodes it with the stdlib `json`
module, and runs `validate/1`: `title` and `author` must be non-blank strings, `year`
must be an integer if present, `isbn` a string if present. On failure it returns 422 with
a per-field `details` map; malformed/non-object JSON returns 400. On success the
`book_store` gen_server allocates a monotonic id via a `'$next_id'` DETS counter, inserts
and `dets:sync`s the row, and the handler replies 201 with the persisted book and a
`Location` header. All storage access is serialised through the single gen_server, so
there are no concurrent-write races. Note: validation rejections use 422 rather than the
400 named in the task's verification hint.
