# Flow

```mermaid
sequenceDiagram
    Client->>books.erl: POST /books {title,author,year,isbn}
    books.erl->>books.erl: do/1 -> route/4
    books.erl->>books.erl: fields/1 (decode JSON, validate title/author)
    books.erl->>DETS: dets:insert_new(books_db, {Id, Book})
    DETS-->>books.erl: ok
    books.erl->>DETS: dets:sync(books_db)
    books.erl-->>Client: 201 {Book} + Location: /books/{id}
```

`do/1` parses the request URI, dispatches on method + path in `route/4`, and wraps the handler in a try/catch that maps `{invalid, Msg}` throws to 400 and any other exception to a logged 500. `POST /books` runs `fields/1` to JSON-decode the body and reject blank/missing `title`/`author` (and non-integer `year` / non-string `isbn`), generates a random 16-byte hex id, inserts with `dets:insert_new`, syncs to disk, and returns 201 with a `Location` header. Item routes (`/books/{id}`) are serialized with `global:trans` per id. Persistence is DETS (OTP's embedded disk term store), not an in-memory map.
