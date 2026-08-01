# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books_app.erl | OTP application callback | `start/2`, `stop/1` |
| src/books_sup.erl | Supervisor: store + http workers (one_for_one) | `start_link/0`, `init/1` |
| src/books_store.erl | `gen_server` over DETS; CRUD + id generation | `create/1`, `list/1`, `get/1`, `update/2`, `delete/1` |
| src/books_http.erl | Raw-TCP HTTP server, request parser, router | `start_link/1`, `route/4` |
| src/books_json.erl | Hand-written JSON encode/decode | `decode/1`, `encode_book/1`, `encode_books/1`, `encode_error/1`, `encode_ok/0` |
| src/books_api.app.src | App resource file (env: port, storage_file) | — |
| test/books_store_tests.erl | EUnit: store CRUD + author filter (3 tests) | `store_test_/0` |
| test/books_http_tests.erl | EUnit: route-level health/validation/create+list (3 tests) | `route_test_/0` |
