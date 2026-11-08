# Evaluation: agent=codex effort=low language=erlang model=gpt-6.1-terra prompt=neutral · rep 2

## Summary

- **Factors:** language=erlang, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — EUnit, via `test_coverage=1.0`
- **Build:** pass — `test_coverage=1.0` from `scores.json` (build + tests ran clean)
- **Lint:** pass — `code_quality=0.956` from `scores.json`
- **Architecture:** `run-summary` skill unavailable in this environment; see inline note below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `books.erl:64` route POST /books → validate + INSERT ... RETURNING *, 201 |
| R2 | GET /books lists all books | ✓ implemented | `books.erl:71` SELECT * FROM books ORDER BY id, 200 |
| R3 | GET /books ?author= filter | ✓ implemented | `books.erl:96` author_filter/1 via uri_string:dissect_query; tested `books_tests.erl:21` |
| R4 | GET /books/{id} single book | ✓ implemented | `books.erl:86` item GET → SELECT WHERE id=; 404 on empty (`books.erl:119`) |
| R5 | PUT /books/{id} updates | ✓ implemented | `books.erl:88` item PUT → UPDATE ... RETURNING *; tested `books_tests.erl:14` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `books.erl:87` item DELETE → DELETE ... RETURNING *; tested `books_tests.erl:15` |
| R7 | Data stored in SQLite | ✓ implemented | `books.erl:126` db/2 shells to sqlite3 CLI against persistent file (BOOKS_DB) |
| R8 | JSON + appropriate status codes | ✓ implemented | `books.erl:37` json:encode; statuses 200/201/400/404/405/500 (`books.erl:124`) |
| R9 | Validation: title & author required | ✓ implemented | `books.erl:101` validate/1 rejects blank/non-binary → 400; tested `books_tests.erl:17` |
| R10 | GET /health | ✓ implemented | `books.erl:63` route → {200, #{status => <<"ok">>}}; tested `books_tests.erl:30` |
| R11 | README with setup/run | ✓ implemented | `README.md` — compile/run, env vars, endpoints, curl examples, test command |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `books_tests.erl:4` — crud, validation, filter, http (4 tests); `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (no re-run per skill §2):

```text
test_coverage = 1.0   → build + all EUnit tests passed
code_quality  = 0.956
defect_rate   = 1.0   → build+test succeeded
```

Tests: `books_tests.erl` — `api_test_/0` fixture spawns the server on an ephemeral
port and exercises CRUD, validation (3 cases), author filter, and a live HTTP
`/health` round-trip. No skipped/disabled tests. The `http/1` test degrades to a
no-op if `books:start/2` returns `{error, eperm}` (sandbox), but under scoring the
server bound and `test_coverage=1.0`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 170 (books.erl 136, books_tests.erl 34) |
| Files | 11 (incl. logs/meta) |
| Dependencies | 0 (stdlib only: gen_tcp, json, uri_string; sqlite3 CLI external) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (scores read from archive) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Query strings on item routes (`/books/{id}?...`) are not stripped, yielding 404 — `books.erl:76,85`
2. [info] SQL built by string concatenation but mitigated by hex-encoding (`CAST(X'..' AS TEXT)`) and digit-only id validation — `books.erl:117,94`
3. [info] HTTP server handles one request per connection (`Connection: close`) — acceptable for scope — `books.erl:38`

## Reproduce

```bash
cd "experiments/adrianco/experiment-93-terra61-deepen/rest-api-crud/runs/agent=codex_effort=low_language=erlang_model=gpt-6.1-terra_prompt=neutral/rep2"
cat scores.json            # mechanical scores (build/test/lint), per skill §2
cat ../../../REQUIREMENTS.json   # pinned 12-requirement checklist
# compile + test (only if re-verifying; scores already stored):
erlc books.erl books_tests.erl
erl -noshell -eval 'case eunit:test(books_tests, [verbose]) of ok -> halt(0); _ -> halt(1) end.'
```
