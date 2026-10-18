# Evaluation: agent=codex_effort=low_language=erlang_model=gpt-6-luna_prompt=neutral · rep 3

*Second-opinion re-check of a prior evaluation (prior requirement_coverage=0.9167, claimed R1-utf8 not met).*

## Summary

- **Factors:** language=erlang, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 11/12 implemented, 1 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 eunit tests, all passed (test_coverage=1.0 from scores.json) / 0 skipped (4 effective)
- **Build:** pass (defect_rate=1.0, scores.json)
- **Lint:** pass — code_quality=1.0
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 1 high, 0 medium, 2 low)

## Second-opinion verdict on the prior claim

**R1-utf8 — CONFIRMED.** I looked for any UTF-8-aware path and there isn't one. `books_json:decode/1` (src/books_json.erl:5) does `binary_to_list`, so each UTF-8 byte becomes its own codepoint. `value/1` (:24) then runs `unicode:characters_to_binary` on those bytes, which double-encodes them. `books_store:sql_value/1` (src/books_store.erl:134) flattens to a list again, and `open_port` args (:97) encode it once more. The read path decodes the sqlite JSON output through the same decoder (:113-128). Probe on a temp copy: POST `{"author":"García"}` stored hex `47617263C383C283C382C2AD61` and returned a 37-byte author where 7 bytes were expected. Any non-ASCII title/author is silently corrupted, so R1 ("persists a book") is only partial.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ~ partial | `books_http.erl:98-101`, `books_store.erl:22-32`; non-ASCII strings corrupted (R1-utf8) |
| R2 | GET /books lists all | ✓ implemented | `books_http.erl:102-104`, `books_store.erl:33-41` |
| R3 | ?author= filter | ✓ implemented | `books_http.erl:147-153`, `books_store.erl:34`; test `crud_and_author_filter_test` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `books_http.erl:105-106`, `select_one` `books_store.erl:78-84`; test asserts 404 |
| R5 | PUT /books/{id} | ✓ implemented | `books_http.erl:107-110`, `books_store.erl:45-56` |
| R6 | DELETE /books/{id} | ✓ implemented | `books_http.erl:111-112` → 204 |
| R7 | SQLite storage | ✓ implemented | `books_store.erl:72-99` sqlite3 file DB |
| R8 | JSON + proper status codes | ✓ implemented | 201/200/204/400/404/500 in `books_http.erl:94-140,173-179` |
| R9 | title/author required | ✓ implemented | `required/1` `books_http.erl:126-130`; test `required_fields_validation_test` |
| R10 | GET /health | ✓ implemented | `books_http.erl:94`; test `health_check_test` |
| R11 | README with setup/run | ✓ implemented | `README.md` |
| R12 | ≥3 tests | ✓ implemented | 4 tests in `test/books_tests.erl`, test_coverage=1.0 |

requirement_coverage = 11/12 = 0.9167 (partial is not counted as implemented).

## Build & Test

Not re-run (per skill). scores.json: test_coverage=1.0, defect_rate=1.0, code_quality=1.0, maintainability=0.599, idiomatic=0.6.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src+test .erl) | 517 |
| Source files | 6 src + 1 test |
| Dependencies | 0 (rebar.config deps []) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |

## Findings

1. [high] R1-utf8: non-ASCII title/author corrupted on create/read
2. [low] SQLite via spawned CLI with string-built SQL
3. [low] No non-ASCII test fixture

## Reproduce

```bash
T=$(mktemp -d); cp -R src $T/; cd $T && erlc -o . src/*.erl
# POST {"title":"T","author":"García"} via books_http:request/4 with books_store:start_link("/tmp/p85.db")
sqlite3 /tmp/p85.db "select hex(author) from books"   # 47617263C383C283C382C2AD61, expected 47617263C3AD61
```
