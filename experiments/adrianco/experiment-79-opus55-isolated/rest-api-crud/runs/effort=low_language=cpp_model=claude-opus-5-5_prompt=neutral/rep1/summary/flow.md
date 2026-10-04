# Flow

```mermaid
sequenceDiagram
    Client->>Server: POST /books (JSON body)
    Server->>App: handle(Request{method,target,body})
    App->>App: route() — match /books, POST
    App->>json: parse(body) + validate title/author
    App->>BookStore: create(BookData)
    BookStore->>SQLite: INSERT ... (prepared, mutex-guarded)
    SQLite-->>BookStore: last_insert_rowid
    BookStore-->>App: Book{id,data}
    App-->>Server: Response{201, to_json(book)}
    Server-->>Client: HTTP/1.1 201 Created + JSON
```

A `POST /books` request is accepted by the thread-per-connection `Server`, which parses the request line/headers (rejecting malformed input with 400 and oversized bodies with 413) and calls `App::handle`. `route()` strips the query string, matches `/books`, and validates the JSON body via `parse_book`: the body must be a JSON object with non-empty string `title` and `author`; `year` must be an integer and `isbn` a string when present, otherwise 400. On success `BookStore::create` runs a mutex-guarded parameterized INSERT and returns the new `Book`, serialized to JSON with a 201. All handler paths are wrapped in a try/catch that converts any exception into a 500, so the transport layer never sees a throw.
