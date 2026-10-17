# Flow

```mermaid
sequenceDiagram
    Client->>server.go: POST /books {json}
    server.go->>server.go: readBookInput (decode, normalize, Validate)
    server.go->>store.go: Create(ctx, in)
    store.go->>store.go: INSERT ... RETURNING id
    store.go-->>server.go: Book{ID, ...}
    server.go-->>Client: 201 + Location header + {json}
```

A `POST /books` request is decoded with `DisallowUnknownFields` under a 1 MiB
`MaxBytesReader`, trimmed via `normalize()`, then validated (title/author required,
year range, ISBN check digit). Valid input is inserted with SQLite's `RETURNING id`,
and the created book is returned as JSON (201) with a `Location` header. Invalid input
returns 400 with per-field problems; routing misses are rewritten to JSON errors.
Input validation, bounded body size, unknown-field rejection, and graceful shutdown
are all present.
