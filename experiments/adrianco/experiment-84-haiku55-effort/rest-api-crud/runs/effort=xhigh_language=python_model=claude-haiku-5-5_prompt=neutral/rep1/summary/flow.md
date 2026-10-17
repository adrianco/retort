# Flow

```mermaid
sequenceDiagram
    Client->>server.py: POST /books {title, author, year, isbn}
    server.py->>server.py: _read_json() (Content-Length guard, JSON parse)
    server.py->>validation.py: validate_book(payload)
    validation.py-->>server.py: BookFields (or ValidationError -> 400)
    server.py->>repository.py: create(fields)
    repository.py->>SQLite: INSERT INTO books ...
    SQLite-->>repository.py: lastrowid
    repository.py-->>server.py: Book
    server.py-->>Client: 201 {json} + Location: /books/{id}
```

A `POST /books` request is read with a `Content-Length` guard (rejecting bodies over 1 MiB with 413 before reading) and parsed as a JSON object. `validate_book()` enforces that `title` and `author` are required non-blank strings, normalises an optional `year` (range-checked) and `isbn` (format-checked, hyphens/spaces stripped), collecting all field errors into a single 400. The validated `BookFields` are inserted via a lock-guarded SQLite connection, and the stored `Book` is returned as 201 with a `Location` header. Errors are centrally mapped in `_dispatch` (`ApiError`→status, `ValidationError`→400, unexpected→500). The server is threaded (`ThreadingHTTPServer`) with a single shared connection serialised by a lock.
