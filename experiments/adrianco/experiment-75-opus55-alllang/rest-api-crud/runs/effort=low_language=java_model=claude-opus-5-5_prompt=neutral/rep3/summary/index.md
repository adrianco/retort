# Summary: java · claude-opus-5-5 · neutral · rep 3

- **Shape:** Java 21 REST API on the built-in JDK `HttpServer`, SQLite via sqlite-jdbc, Jackson for JSON.
- **Structure:** 2 source modules + 1 test module (259 LOC total).
- **Interfaces:** 6 HTTP routes (5 CRUD + /health), one `books` SQLite table, one `Book` record.
- **Notable:** No framework — plain `com.sun.net.httpserver`; compact functional style using records, `switch` expressions, and `Optional`. Repository methods each open a per-call connection and are `synchronized`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
