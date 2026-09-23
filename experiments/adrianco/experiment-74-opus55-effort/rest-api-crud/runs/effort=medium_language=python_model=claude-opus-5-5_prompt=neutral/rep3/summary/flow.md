# Flow

```mermaid
sequenceDiagram
    Client->>BookHandler: POST /books {title, author, ...}
    BookHandler->>handle_request: (store, "POST", "/books", body)
    handle_request->>validate_book: parse + validate payload
    validate_book-->>handle_request: normalised book
    handle_request->>BookStore: create(book)
    BookStore-->>handle_request: row (with id)
    handle_request-->>BookHandler: (201, book)
    BookHandler-->>Client: 201 application/json
```

A `POST /books` is read by `BookHandler._dispatch` (which enforces a 1 MiB body cap), then dispatched through the framework-independent `handle_request`. The body is JSON-parsed and passed to `validate_book`, which requires non-empty `title`/`author`, range-checks `year`, validates/normalises `isbn`, and rejects unknown fields. The validated dict is inserted by `BookStore.create` under a lock; a duplicate ISBN raises `ConflictError` → 409. Notable: routing is deliberately separated from the HTTP layer so it is unit-testable without a live socket; all DB access is serialized through a single `threading.Lock`.
