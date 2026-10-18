# Flow

```mermaid
sequenceDiagram
    Client->>books_collection_handler: POST /books {json}
    books_collection_handler->>books_http: read_json_body(Req)
    books_http-->>books_collection_handler: {ok, Body}
    books_collection_handler->>books_validate: validate(Body)
    books_validate-->>books_collection_handler: {ok, Attrs}
    books_collection_handler->>books_db: insert(Attrs)
    books_db->>esqlite3: INSERT + last_insert_rowid
    esqlite3-->>books_db: Id
    books_db-->>books_collection_handler: #{id,title,...}
    books_collection_handler-->>Client: 201 {json} + Location
```

A `POST /books` reads and JSON-decodes the body, validates it (title/author required, year/isbn optional and null-defaulted), and on success calls the `books_db` gen_server, which serialises the `INSERT` against the single SQLite connection and returns the persisted row. The handler replies `201` with the book JSON and a `Location: /books/{id}` header. Validation failures short-circuit to `400` with a `details` list; malformed JSON returns `400` before validation. All DB access is funnelled through one gen_server process, so writes are serialised; esqlite3 errors are turned into process crashes so the supervisor restarts the DB owner rather than returning corrupt state.
