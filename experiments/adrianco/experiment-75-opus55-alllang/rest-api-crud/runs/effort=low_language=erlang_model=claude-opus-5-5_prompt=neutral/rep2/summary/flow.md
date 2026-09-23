# Flow

```mermaid
sequenceDiagram
    Client->>books_http: POST /books {json}
    books_http->>books_http: parse request line + headers, read body
    books_http->>books_api: handle(<<"POST">>, "/books", Query, Body)
    books_api->>books_api: json:decode + validate/1
    books_api->>books_store: create(Book)
    books_store->>books_store: dets:insert + dets:sync
    books_store-->>books_api: StoredBook (with id)
    books_api-->>books_http: {201, StoredBook}
    books_http-->>Client: HTTP/1.1 201 {json}
```

A request to `POST /books` is read off the socket by `books_http:conn/1` (packet mode `http_bin`), which extracts the method, path, query and body, then calls `books_api:handle/4`. The API layer decodes the JSON body, runs `validate/1` (rejecting blank `title`/`author` with `400` and a `details` list), and on success calls the `books_store` gen_server, which persists the record to DETS with an auto-incremented id and syncs to disk. The stored book is serialised back with `json:encode` and returned as `201 Created`. The server is fully dependency-free — HTTP parsing, JSON (OTP 27+ `json` module) and storage (DETS) all use the standard library. Each connection is handled in its own spawned process; connections are kept alive unless `Connection: close` is sent.
