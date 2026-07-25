# Summary: language=cpp · model=claude-fable-5 · prompt=neutral · rep 1

- **Shape:** C++17 REST API using cpp-httplib + nlohmann/json + SQLite (vendored header-only deps).
- **Structure:** 3 source modules (main / api / book_store) + 1 integration test file, built with CMake + CTest.
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter), one `books` SQLite table.
- **Notable:** Thread-safe store (mutex + RAII prepared statements), `std::variant`-based validation, server-wide exception handler, tests run a real server on an ephemeral port. Clean separation of transport (api) from persistence (book_store).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
