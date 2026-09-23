# Summary: effort=low_language=java_model=claude-opus-5-5_prompt=neutral · rep 2

- **Shape:** Java REST CRUD on the JDK built-in `com.sun.net.httpserver.HttpServer` with SQLite (sqlite-jdbc) persistence and Jackson JSON — no web framework.
- **Structure:** 2 source modules + 1 test module (~265 Java LOC), 3 runtime/test dependencies.
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), one `books` SQLite table.
- **Notable:** Very compact, dependency-light approach — leans on the standard library `HttpServer` instead of Spring/Javalin. Uses records + pattern matching (`Resp`, `instanceof Resp r`), a single `handle()` error funnel, and per-call JDBC connections guarded by `synchronized`. Tests spin up the real server on an ephemeral port and exercise it over HTTP.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
