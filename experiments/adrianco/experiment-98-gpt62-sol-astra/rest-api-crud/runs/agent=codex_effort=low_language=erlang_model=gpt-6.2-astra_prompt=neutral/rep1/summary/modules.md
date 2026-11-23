# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| books.erl | inets `mod` HTTP handler, routing, DETS persistence, validation | `start/2`, `stop/1`, `run/0`, `do/1` |
| books_tests.erl | EUnit handler-level tests driving `books:do/1` directly | `api_test_/0` (health, validation, lifecycle, filter) |
| Makefile | `build` (erlc -Werror), `test` (EUnit), `run` targets | — |
| README.md | Setup/run instructions, route table | — |
