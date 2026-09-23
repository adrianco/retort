# Flow

```mermaid
sequenceDiagram
    Client->>books_http: POST /books {json}
    books_http->>books_http: parse request line, headers, body
    books_http->>books_api: handle("POST", "/books", Body)
    books_api->>books_api: json:decode + validate/1
    books_api->>books_db: create(Book) (gen_server call)
    books_db->>books_db: dets:insert + dets:sync
    books_db-->>books_api: {ok, Book#{id}}
    books_api-->>books_http: {201, Book}
    books_http-->>Client: 201 {json}
```

A request is parsed by `books_http:handle_conn/1` using `gen_tcp` with `{packet, http_bin}`,
then dispatched to `books_api:handle/3`, which splits the path/query and routes. For a create,
the body is `json:decode`d and passed through `validate/1` (title and author are required
non-empty strings; year must be an integer if present; isbn a string if present). On success the
validated book is inserted into DETS via the `books_db` gen_server, which assigns an integer id
and `dets:sync`s to disk, then the book is JSON-encoded with a 201. Handler exceptions are caught
in `books_http:safe_handle/3` and returned as 500. Note: DETS is used as the embedded store in
place of SQLite (a deliberate, README-documented choice to stay dependency-free).
