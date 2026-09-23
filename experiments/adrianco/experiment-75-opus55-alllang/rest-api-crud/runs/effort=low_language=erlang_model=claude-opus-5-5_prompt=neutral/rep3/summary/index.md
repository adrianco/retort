# Summary: effort=low_language=erlang_model=claude-opus-5-5_prompt=neutral · rep 3

- **Shape:** Erlang/OTP REST API — hand-rolled `gen_tcp` HTTP/1.1 server, DETS embedded store, supervised OTP application, zero third-party deps.
- **Structure:** 5 source modules (~205 LOC) + 1 EUnit test file (76 LOC).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), full JSON responses with 200/201/204/400/404/405/500 status codes.
- **Notable:** Uses OTP 27's built-in `json` module and DETS instead of SQLite to stay dependency-free (documented in README). Clean OTP structure: gen_server DB behind a supervisor, per-connection HTTP process, exceptions caught into 500s.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
