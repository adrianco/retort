# Run Summary — Books REST API (Erlang)

## Surface

A dependency-free Erlang/OTP REST service for a book collection. It implements
full CRUD over `/books`, an `?author=` list filter, input validation, and a
`/health` check, returning JSON with appropriate status codes. Persistence is
via OTP's built-in **DETS** (the "language-equivalent embedded DB" in place of
SQLite). No third-party deps — the HTTP server, JSON codec, and store are all
hand-rolled on `kernel`/`stdlib`.

## Architecture

An OTP application (`books_app`) starts a `one_for_one` supervisor
(`books_sup`) with two permanent workers:

- **`books_store`** — a `gen_server` owning a DETS table; serializes all
  create/list/get/update/delete calls and generates monotonic integer ids via a
  `'$next_id'` counter row.
- **`books_http`** — a `gen_server` that listens on a raw TCP socket, accepts
  connections in a loop, and spawns one process per request. Each request is
  parsed by hand (request line + headers + Content-Length body), routed by
  `route/4`, and answered with a hand-built HTTP/1.1 response.

`books_json` is a hand-written JSON encoder/decoder (objects, strings,
non-negative integers, null only).

## Flow

```
TCP accept → serve/1 → read_request/2 (parse headers + body)
           → route(Method, Target, Headers, Body)
               → books_json:decode / validation
               → books_store:{create,list,get,update,delete}  (gen_server → DETS)
               → books_json:encode_* → send/3 (HTTP/1.1 response)
```

See `modules.md` and `interfaces.md` for the per-file and per-endpoint detail.
