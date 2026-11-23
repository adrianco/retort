# Flow

```mermaid
sequenceDiagram
    Client->>Books.m: POST /books {title,author,year,isbn}
    Books.m->>request(): parse request line + headers + body
    request()->>route(): method, target, body
    route()->>route(): validate title/author non-blank, year int, isbn string
    route()->>SQLite: INSERT ... RETURNING *
    SQLite-->>route(): new row
    route()-->>serve(): dict + status=201
    serve()-->>Client: 201 {json book}
```

A request arrives over a TCP socket (or stdin in `--stdio` mode). `request()` parses the
request line and headers, enforcing a single numeric `Content-Length` and rejecting
`Transfer-Encoding`, then reads the exact body. `route()` dispatches on method+path: for
POST it parses the JSON object, rejects a missing/blank `title` or `author` (400), type-checks
optional `year`/`isbn`, and runs a parameterized `INSERT ... RETURNING *` so the response echoes
the stored row including its new integer `id`. `serve()` serializes the result to JSON and writes
an HTTP/1.1 response with the matching status phrase and `Connection: close`.

Notable: whole service is one 161-line Objective-C file with no external HTTP framework —
hand-rolled HTTP/1.1 parsing. SQL uses parameterized statements and `RETURNING` throughout
(no SQL injection, no read-after-write race). Author filter is exact and case-sensitive.
No pagination (not required).
