# Summary: effort=low language=java model=claude-haiku-5-5 prompt=neutral · rep 3

- **Shape:** Java 17 REST API on the JDK's built-in `com.sun.net.httpserver` HTTP server, Jackson for JSON, SQLite (xerial sqlite-jdbc) for storage — no web framework.
- **Structure:** 6 main modules + 1 test file (12 test methods); Maven build with shade plugin for a runnable jar.
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter), 2 record types, `BookRepository` + `BookValidator` library API.
- **Notable:** Dependency-light (no Spring); clean layering (server/repository/validator); goes beyond spec with ISBN-10/13 check-digit validation, year-range checks, 405/400 edge-case handling, and a `Location` header on create.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
