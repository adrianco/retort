# Evaluation: effort=max language=python model=claude-sonnet-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=max
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** all passed / 0 failed / 0 skipped (125 test functions, ~250+ parametrized cases; effective = 125)
- **Build:** pass — from `scores.json` (`defect_rate=1.0`, `test_coverage=0.99`)
- **Lint:** pass — `code_quality=0.83` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Mechanical scores read from `scores.json` (inline gate output; not re-run):
`test_coverage=0.99`, `defect_rate=1.0`, `code_quality=0.83`, `maintainability=0.91`,
`idiomatic=0.92`, `token_efficiency=0.00176`.

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/bookapi/app.py:_create_book` → `repository.py:create` (INSERT), returns 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `app.py:_list_books` → `repository.py:list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `repository.py:list_books` `WHERE casefold(author)=?`; `app.py:_list_books` reads query param |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.py:_get_book` raises 404 via `_book_not_found()` when `repository.get` is None |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:_update_book` → `repository.py:update` (UPDATE, None→404) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:_delete_book` → `repository.py:delete`, returns 204 |
| R7 | Data stored in SQLite | ✓ implemented | `repository.py` uses `sqlite3`, `CREATE TABLE books`, AUTOINCREMENT PK |
| R8 | JSON responses + status codes | ✓ implemented | `web.py:Response.send` emits JSON; 201/200/204/400/404/405/413/500 across `app.py` |
| R9 | title & author required | ✓ implemented | `validation.py:_FIELDS` marks title/author `required=True`; blank/missing → 400 |
| R10 | GET /health | ✓ implemented | `app.py:_health` pings DB, returns `{"status":"ok"}` (503 if DB down) |
| R11 | README with setup/run | ✓ implemented | `README.md` (11.7 KB) has Requirements / Setup / Run sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 125 test functions in `tests/`; `test_coverage=0.99` |

No prompt-factor (`prompts/neutral.md`) requirements beyond R12: the neutral prompt only
asks to "include tests that demonstrate the implementation meets the requirements."

## Build & Test

Not re-run — mechanical scores taken from the inline gate's `scores.json`:

```text
test_coverage = 0.99   # build succeeded + test suite executed and passed
defect_rate   = 1.0    # build+test success
code_quality  = 0.83   # lint/quality score
```

Test inventory (grep, not executed):

```text
tests/test_api.py         55 test functions (14 parametrized)
tests/test_server.py      25 test functions (3 parametrized)
tests/test_repository.py  25 test functions (1 parametrized)
tests/test_validation.py  20 test functions (9 parametrized)
tests/conftest.py         fixtures only
skips/xfail: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src only) | 715 |
| Lines of code (tests) | 1508 |
| Files (excl. artifacts) | 23 |
| Dependencies (runtime) | 0 (stdlib only; 2 test deps) |
| Tests total | 125 functions (~250+ cases) |
| Tests effective | 125 (0 skipped) |
| Skip ratio | 0% |
| test_coverage | 0.99 |

## Findings

Top 5 by severity (full list in `findings.jsonl`) — all informational; no deductions:

1. [info] E1 — Robust HTTP semantics beyond spec (HEAD/OPTIONS/405/Allow)
2. [info] E2 — Security/correctness hardening (nosniff, 1MB body cap, chunked rejection, log escaping)
3. [info] E3 — Test suite far exceeds the 3-test minimum (125 functions, coverage 0.99)
4. [info] R8-note — Case-insensitive Unicode author filter and UTF-8 query decoding

## Reproduce

```bash
cd "experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=max_language=python_model=claude-sonnet-5-5_prompt=neutral/rep1"
cat scores.json                                   # mechanical scores (not re-run)
cat ../../../REQUIREMENTS.json                     # pinned 12-item checklist
grep -rhE "def test_" tests/ --include="*.py" | wc -l   # 125
grep -rnE "pytest\.skip|xfail" tests/ --include="*.py" | wc -l   # 0
find src -name '*.py' | xargs wc -l | tail -1     # 715
```
