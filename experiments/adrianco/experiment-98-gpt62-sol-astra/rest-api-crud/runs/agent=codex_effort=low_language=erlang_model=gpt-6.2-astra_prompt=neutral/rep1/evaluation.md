# Evaluation: agent=codex effort=low language=erlang model=gpt-6.2-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=erlang, model=gpt-6.2-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — from `test_coverage=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.956` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

A complete, stdlib-only Erlang/OTP implementation: inets `httpd` with a single `mod` callback, OTP's `json` codec, and DETS for embedded persistence. Build and all EUnit tests pass per the stored scores; every pinned requirement is satisfied.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `books.erl:54` route + `fields/1` validate+persist via `dets:insert_new` |
| R2 | GET /books lists all books | ✓ implemented | `books.erl:43-53` `dets:foldl` collects all |
| R3 | GET /books supports ?author= filter | ✓ implemented | `books.erl:46-48` filters on `author` query param (exact match) |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `books.erl:71-75` `item("GET"...)`, `missing()` on `[]` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `books.erl:76-82` `item("PUT"...)`, 404 if absent |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `books.erl:83-87` `dets:select_delete`, 200/404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `books.erl:12` DETS (OTP embedded disk store), `books.dets` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `books.erl:37-40` `json:encode`; codes 200/201/400/404/405/500 |
| R9 | Input validation: title & author required | ✓ implemented | `books.erl:98-102` rejects blank/missing title/author (400) |
| R10 | GET /health endpoint | ✓ implemented | `books.erl:42` returns `200 {status:ok}` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — make build/test/run, curl example, route table |
| R12 | At least 3 unit/integration tests | ✓ implemented | `books_tests.erl` — health, validation, lifecycle, filter (4); `test_coverage=1.0` |

## Build & Test

Build and tests were not re-run — scores read from `scores.json` (inline gate during `retort run`):

```text
test_coverage = 1.0   → make build (erlc -Werror) + EUnit all passed
code_quality  = 0.956 → lint/quality
defect_rate   = 1.0   → build+test succeeded
```

Test suite (`books_tests.erl`) drives `books:do/1` directly against a temp DETS file:
- `health` — GET /health → 200 {status:ok}
- `validation` — 5 malformed POST bodies each → 400
- `lifecycle` — create → get → update → get → delete → 404 → put-missing-404
- `filter` — two authors, list-all, ?author= exact match, ?author=Nobody → []

No skipped/ignored/disabled tests (`grep` for skip/ignore → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 165 (books.erl 105, books_tests.erl 60) |
| Files | 12 (incl. logs/meta/artifacts) |
| Dependencies | 0 (empty `rebar.lock`, stdlib only) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores from gate) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; no defects:

1. [info] `?author=` filter is exact-match only — acceptable for R3 (`books.erl:48`)
2. [info] PUT /books/{id} is a full replace, not a partial update — valid REST semantic (`books.erl:76`)
3. [info] Low idiomatic score (0.3) despite clean stdlib-only approach (`scores.json`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=erlang_model=gpt-6.2-astra_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores (test_coverage=1.0)
cat ../../../REQUIREMENTS.json                     # pinned 12-requirement checklist
grep -rnE "skip|ignore" . --include="*.erl" | wc -l  # 0 skips
# Build/test (optional — scores already stored):
make test                                          # erlc -Werror + EUnit
```
