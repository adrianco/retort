# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `Books.h` | Public seam between transport and domain logic | `InitializeBooks()`, `HandleBooks()` |
| `Books.m` | Schema, validation, routing, SQLite-backed CRUD handler | `InitializeBooks()`, `HandleBooks()` |
| `Server.m` | HTTP/1.1 transport: socket, request parse, response serialize | `main()` |
| `Tests.m` | Integration tests driving `HandleBooks()` against SQLite | `main()`, `TestCRUD`, `TestFilter`, `TestValidationAndHealth`, `TestPersistence` |
| `Makefile` | Build + test targets (clang, `-Wall -Wextra -Werror`, ARC) | `all`, `test`, `clean` |
| `README.md` | Setup, run instructions, route table | — |
