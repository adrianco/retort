# Flow

A request opens a fresh `sqlite3` connection per handler, executes, and closes it
inline; there is no connection pool, ORM, blueprint, or app factory.

```mermaid
flowchart TD
    C[Client] -->|HTTP JSON| F[Flask app.py]
    F --> H{route}
    H -->|GET /health| HC[health_check → 200]
    H -->|POST /books| V{title & author keys present?}
    V -->|no| E400[400 error JSON]
    V -->|yes| I[INSERT + SELECT lastrowid → 201]
    H -->|GET /books| Q{?author= given?}
    Q -->|yes| L1[SELECT ... WHERE author LIKE %v%]
    Q -->|no| L2[SELECT *]
    L1 --> R200[200 JSON list]
    L2 --> R200
    H -->|GET/PUT/DELETE /books/id| X{row exists?}
    X -->|no| E404[404 error JSON]
    X -->|yes| OP[SELECT / UPDATE / DELETE → 200]
    I --> DB[(books.db)]
    OP --> DB
    L1 --> DB
    L2 --> DB
```

Startup: `init_db()` runs `CREATE TABLE IF NOT EXISTS` only from the `__main__`
guard, so an importer of `app` (including `test_app.py`) must call it explicitly.
