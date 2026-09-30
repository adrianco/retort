# Flow

```mermaid
sequenceDiagram
    Client->>Handler: POST /books {title, author, year, isbn}
    Handler->>Handler: _body() parse JSON
    Handler->>validate: validate(data)
    validate-->>Handler: cleaned dict (or 400)
    Handler->>BookStore: create(data)
    BookStore->>SQLite: INSERT ... ; SELECT row
    SQLite-->>BookStore: row
    BookStore-->>Handler: book dict
    Handler-->>Client: 201 {json}
```

A `POST /books` reads the body, parses JSON (`_body`, 400 on malformed), runs `validate` (title/author required non-empty strings, year must be int, isbn must be str), inserts under a `threading.Lock`, re-selects the inserted row, and returns it with 201. All mutating store methods hold the lock, so the `ThreadingHTTPServer` is safe against concurrent writes to the single shared connection. Validation errors and JSON errors surface as 400; a catch-all maps unexpected exceptions to 500.
