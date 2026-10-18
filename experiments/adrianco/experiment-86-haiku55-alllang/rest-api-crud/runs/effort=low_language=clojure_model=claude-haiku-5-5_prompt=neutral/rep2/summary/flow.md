# Flow

```mermaid
sequenceDiagram
    Client->>handler.clj: POST /books {json}
    handler.clj->>handler.clj: parse-body (JSON → map)
    handler.clj->>validation.clj: validate-book
    validation.clj-->>handler.clj: nil (valid)
    handler.clj->>validation.clj: normalize-book
    handler.clj->>db.clj: create-book! ds fields
    db.clj->>SQLite: INSERT ... RETURNING *
    SQLite-->>db.clj: stored row
    db.clj-->>handler.clj: book map
    handler.clj-->>Client: 201 {json book}
```

A `POST /books` request is routed by `make-handler*`, its body slurped and parsed to a keyword-keyed map by `parse-body` (a non-object or malformed body yields `400`). `validate-book` enforces that `title` and `author` are non-blank strings and that `year`/`isbn`, when present, have the right types; failures return `422` with a per-field `fields` map. On success the fields are trimmed by `normalize-book` and inserted via next.jdbc's `INSERT ... RETURNING *`, and the stored row is returned as JSON with `201`. Routing is hand-rolled over path segments; `wrap-params` supplies the `?author=` query filter for `GET /books`. Error handling is centralized in a top-level `try/catch` that logs to stderr and returns `500`.
