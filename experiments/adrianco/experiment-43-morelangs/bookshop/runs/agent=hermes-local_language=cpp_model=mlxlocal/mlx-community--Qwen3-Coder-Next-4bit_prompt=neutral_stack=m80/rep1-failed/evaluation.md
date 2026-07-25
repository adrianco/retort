# Evaluation: cpp · hermes-local · Qwen3-Coder-Next-4bit · m80 · rep 1 (SECOND OPINION)

## Summary

- **Factors:** language=cpp, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, agent=hermes-local, prompt=neutral, stack=m80
- **Status:** ok (build + tests pass; two real correctness defects in the HTTP/serialization layer)
- **Requirements:** 10/12 implemented, 1 partial (R2), 1 missing (R8)
- **Requirement coverage:** 0.833 (was 0.75 in first eval — corrected, see below)
- **Tests:** pass (test_coverage=1.0 from scores.json); server integration tests self-skip 3 assertions
- **Build:** pass — from scores.json (test_coverage=1.0, defect_rate=0.964)
- **Lint:** code_quality=0.967 from scores.json
- **Findings:** 3 items in `findings.jsonl` (0 critical, 2 high, 1 medium)

## Second-opinion verdict on the prior evaluation

The first evaluation claimed three requirements unmet. **All three technical claims are
CONFIRMED against the code** — the first evaluator did not invent anything. However, two of
the three claims (R8-a and R8-b) are two facets of the *same* pinned requirement **R8**, so
counting them as two separate failed requirements double-counted and drove coverage to 0.75
(9/12). The correct count of pinned requirements not fully met is **two** — R2 (partial) and
R8 (missing) — giving **coverage = 10/12 = 0.833**.

| Prior claim | Verdict | Evidence checked |
|----|----|----|
| R8-a: every response returns 404, no routes registered | **CONFIRMED** | `main.cpp:27` calls only `setDefaultHandler`; `handlers_` map stays empty, so `server.cpp:169` find() always misses → default branch `server.cpp:174-177` sets `status_code=404`. Response *bodies* are correct (routing works via the default handler → `handler.cpp:136`), but the HTTP status line is always 404 — including GET /health. |
| R2: GET /books emits malformed JSON (unterminated isbn) | **CONFIRMED** | `handler.cpp:211` ends `<< jsonEscape(book.isbn) << "}"` — missing the closing `\"`. Correct single-book path at `handler.cpp:264` ends `<< "\"}"`. List output is invalid JSON. |
| R8-b: status codes never differentiated (no 201/400/404) | **CONFIRMED — same requirement as R8-a** | `handleRequest` (`handler.cpp:136`) returns only a body string; `server.cpp:172-177` hardcodes 200 (matched) / 404 (default). `generateResponse` supports 201/400/404/500 but they are never passed. Collapses into R8. |

Net change: **requirement_coverage 0.75 → 0.833** (R8-a and R8-b are one requirement). The
defects themselves stand.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/handler.cpp:161-197` parses body, validates, `db_.createBook` |
| R2 | GET /books lists all books | ~ partial | `src/handler.cpp:199-221` route exists but line 211 emits malformed JSON (unterminated isbn) |
| R3 | GET /books ?author= filter | ✓ implemented | `src/handler.cpp:200`, `db_.getAllBooks(author_filter)`; `database.cpp:84` binds filter |
| R4 | GET /books/{id} single book | ✓ implemented | `src/handler.cpp:255-267`, `db_.getBookById`, "Book not found" on miss |
| R5 | PUT /books/{id} update | ✓ implemented | `src/handler.cpp:225-245`, `db_.updateBook` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `src/handler.cpp:247-253`, `db_.deleteBook` |
| R7 | SQLite / embedded DB storage | ✓ implemented | `src/database.cpp:14` `sqlite3_open`, prepared statements throughout |
| R8 | JSON + appropriate HTTP status codes | ✗ missing | every response is HTTP 404 (`server.cpp:166-178`); 201/400/404-semantics never emitted; + malformed list JSON |
| R9 | Validation: title & author required | ✓ implemented | `src/handler.cpp:172-183` `BookValidator::validate` returns error JSON (status is wrong — see R8) |
| R10 | GET /health | ✓ implemented | `src/handler.cpp:141-143` returns `{"status":"healthy"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` present (2437 bytes) |
| R12 | ≥3 tests, tests run | ✓ implemented | `tests/` has 5 test binaries; test_coverage=1.0 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage   = 1.0     (build + tests pass)
code_quality    = 0.967
defect_rate     = 0.964
maintainability = 0.870
idiomatic       = 0.60
```

Server integration tests (`tests/test_server.cpp:138,172,206`) print `SKIP:` and bypass the
get/update/delete assertions when create returns no ID over HTTP — the passing coverage is
carried by the direct database tests; the HTTP path is not verified end-to-end. The agent's
own README (`_agent_stdout.log`) documents a "Known Issue" with the HTTP POST path.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src+include+tests) | 1353 |
| Files (src/include/tests) | 16 |
| Dependencies | sqlite3 (system), pthread |
| Tests | 5 test binaries; test_coverage=1.0 |
| Conditional self-skips | 3 (server get/update/delete) |

## Findings

Top items (full list in `findings.jsonl`):

1. [high] R8 — every HTTP response returns 404; status codes never differentiated (`server.cpp:166-178`)
2. [high] R2 — GET /books emits malformed JSON, unterminated isbn (`handler.cpp:211` vs `:264`)
3. [medium] Server integration tests self-skip get/update/delete assertions (`test_server.cpp:138,172,206`)

## Reproduce

```bash
cd runs/agent=hermes-local_language=cpp_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep1
sed -n '211p;264p' src/handler.cpp        # malformed vs correct isbn serialization
sed -n '164,178p' src/server.cpp          # hardcoded 200/404 dispatch
sed -n '26,30p' src/main.cpp              # only setDefaultHandler, no addHandler
cat scores.json                           # test_coverage=1.0, code_quality=0.967
```
