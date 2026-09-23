# Architecture summary — books_api

> The `run-summary` skill is not registered as an invocable skill in this session;
> this is a hand-written stand-in based on reading the source. See `../README.md`
> ("Project layout") for the author's own map.

## Modules

- **`books_api/__main__.py`** (29 LOC) — CLI/env entry point (`--host/--port/--db`,
  `BOOKS_*` env), builds the server via `create_server`, runs `serve_forever`, closes
  the store on exit.
- **`books_api/server.py`** (203 LOC) — HTTP layer. `BookRequestHandler` (stdlib
  `BaseHTTPRequestHandler`, HTTP/1.1 keep-alive) dispatches by path+method to `/health`,
  `/books`, `/books/{id}`. `HTTPError` carries status/message/details; `_send_json`
  centralises JSON encoding + Content-Length. `BookServer` is a `ThreadingHTTPServer`
  holding the shared `BookStore`.
- **`books_api/store.py`** (92 LOC) — SQLite persistence. Single shared connection behind
  a `threading.Lock` (so `:memory:` and concurrent threads work). `create/list/get/
  update/delete/ping`; unique `isbn` → `DuplicateISBNError`; case-insensitive author index.
- **`books_api/validation.py`** (71 LOC) — pure `validate_book(payload)` returning a
  normalised dict or raising `ValidationError(errors)`; required title/author, optional
  bounded year, optional normalised ISBN-10/13, rejects unknown fields.

## Flow

Request → `_dispatch` (route match + method lookup) → handler → `store` (locked SQLite) →
`_send_json`. Validation errors and not-found are raised as `HTTPError` and rendered as
`{"error", "details"}`; unexpected exceptions become a 500.

## Layering

`__main__ → server → {store, validation}`. Clean separation: HTTP concerns, persistence,
and validation are independent and independently unit-tested (`tests/test_store.py`,
`tests/test_validation.py`, `tests/test_api.py` end-to-end against a live server).
