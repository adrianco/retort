# Summary: effort=low_language=cpp_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** C++17 REST API — hand-rolled POSIX-socket HTTP/1.1 server + SQLite storage, single external dependency (`-lsqlite3`).
- **Structure:** 3 source modules (header + impl + server) and 1 test file (25 `CHECK` assertions in one binary).
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter); one testable `BookApi::handle()` seam decoupled from sockets.
- **Notable:** Dependency-light — includes a hand-written JSON parser/serializer and URL decoder rather than pulling a library. Parameterized SQL throughout; validation and status codes match the spec. Server is single-threaded/blocking (no concurrency), which is fine for the task scope.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
