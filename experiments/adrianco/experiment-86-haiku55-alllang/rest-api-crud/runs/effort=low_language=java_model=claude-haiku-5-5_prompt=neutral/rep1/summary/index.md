# Summary: effort=low language=java model=claude-haiku-5-5 prompt=neutral · rep 1

- **Shape:** Java 21 REST API on the JDK built-in `HttpServer`, Jackson for JSON, SQLite via `sqlite-jdbc` (JDBC)
- **Structure:** 5 main modules + 1 test file (6 integration tests)
- **Interfaces:** 6 HTTP routes (full CRUD + `?author=` filter + `/health`), 1 SQLite table
- **Notable:** No web framework — uses the JDK's `com.sun.net.httpserver` directly; `record` types for `Book`/`BookInput`; single shared JDBC connection with `synchronized` methods; validation lives on the input record (year range + ISBN format beyond spec)

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
