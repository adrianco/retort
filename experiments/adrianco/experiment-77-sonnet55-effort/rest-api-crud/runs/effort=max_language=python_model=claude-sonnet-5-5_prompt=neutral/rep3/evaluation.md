# Evaluation: effort=max_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=max
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 115 tests, all pass / 0 failed / 0–5 skipped (platform-conditional; effective ≥110 on this host) — `test_coverage=0.99` from `scores.json`
- **Build:** pass — `defect_rate=1.0`, `test_coverage=0.99` (stdlib-only, no build step)
- **Lint:** pass — `code_quality=0.833` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 4 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:_create_book` → `repository.py:create_book`; `test_api.py:26` asserts 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:_list_books` → `repository.py:list_books`; ordered by id |
| R3 | GET /books ?author= filter | ✓ implemented | `repository.py:list_books` `WHERE fold(author)=?`; `test_api.py:260-269` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:_get_book` raises `_book_not_found` when None |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:_update_book` → `repository.py:update_book`, 404 if absent |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:_delete_book` → `repository.py:delete_book`, 204/404 |
| R7 | SQLite / embedded store | ✓ implemented | `repository.py` sqlite3 + `_SCHEMA`, file-backed with `:memory:` option |
| R8 | JSON + correct status codes | ✓ implemented | `web.py:json_response`; 201/200/204/400/404/405/413/500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `validation.py:validate_book` required parsers; `test_validation.py` (16 tests) |
| R10 | GET /health | ✓ implemented | `app.py:_health` pings DB, 200/503; `test_api.py:33-50` |
| R11 | README with setup/run | ✓ implemented | `README.md` (12.9 KB) present with setup and run instructions |
| R12 | ≥3 tests that run | ✓ implemented | 115 test functions across 4 test modules; `test_coverage=0.99` |

Prompt factor `neutral` (prompts/neutral.md) prescribes no methodology and adds no checkable P-requirements.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.99   (build + all tests pass; 99% branch coverage)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.8333
maintainability = 0.9168
idiomatic     = 0.9
```

Test inventory (grep): `def test_` × 115 (test_api 55, test_server 23, test_repository 21, test_validation 16). Skips are 4 platform `skipif` guards + 1 conftest socket-bind guard; none are unconditional disables.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 647 |
| Lines of code (tests) | 1511 |
| Files (source + tests) | 12 |
| Runtime dependencies | 0 (stdlib only) |
| Test dependencies | 2 (pytest, pytest-cov) |
| Tests total | 115 |
| Tests effective | ≥110 (host-dependent; platform skips excluded) |
| Skip ratio | ≤4.3% (conditional platform guards) |
| Branch coverage | 99% |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] Four platform-conditional test skips (`skipif` POSIX/Windows guards) — run on this host; acceptable
2. [info] Live-server fixture skips if loopback socket cannot bind (sandbox guard)
3. [info] Implementation exceeds spec: Content-Length/64 KiB body caps, chunked-body rejection, log-injection escaping, Unicode-normalised case-insensitive author filter, threaded server with per-request timeouts

No requirement is missing or partial; no build/test/lint failures.

## Reproduce

```bash
cd "experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=max_language=python_model=claude-sonnet-5-5_prompt=neutral/rep3"
cat scores.json                                   # stored mechanical scores (no re-run)
cat ../../../REQUIREMENTS.json                    # pinned 12-requirement checklist
grep -rhE "def test_" tests/ | wc -l              # 115 test functions
grep -rnE "pytest\.skip|@pytest\.mark\.skip" tests/  # 5 conditional skips
# Optional full run: python -m pytest (pytest>=8, pytest-cov>=5)
```
