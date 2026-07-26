# Flow

```mermaid
sequenceDiagram
    Client->>main.py: POST /books {title, author, year, isbn}
    main.py->>models.py: BookCreate validation
    models.py-->>main.py: validated payload (or 400)
    main.py->>database.py: create_book(conn, data)
    database.py->>SQLite: INSERT INTO books
    database.py-->>main.py: stored book dict
    main.py-->>Client: 201 {json} + Location header
```

A `POST /books` request is validated by the `BookCreate` Pydantic model (required `title`/`author`, optional bounded `year`, normalised `isbn`); validation failures are caught by a custom `RequestValidationError` handler returning a uniform 400 `{detail, errors}` body. On success a per-request SQLite connection (dependency-injected via `get_conn`) inserts the row; a duplicate ISBN surfaces as `sqlite3.IntegrityError` → 409. The stored resource is returned as 201 with a `Location` header. Notable: connection-per-request pattern, custom exception handlers for uniform JSON errors, both PUT (full replace) and PATCH (partial) supported beyond the spec, LIKE-wildcard escaping on the author filter.
