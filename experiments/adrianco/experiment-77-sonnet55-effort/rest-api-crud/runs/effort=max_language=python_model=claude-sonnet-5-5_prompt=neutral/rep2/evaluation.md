# Evaluation: effort=max language=python model=claude-sonnet-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=max
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 172 test functions, 0 skipped (172 effective); test_coverage=0.99 (build + all tests pass)
- **Build:** pass — from `scores.json` (`test_coverage=0.99`, `defect_rate=1.0`); not re-run
- **Lint:** pass — `code_quality=0.833` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Scores read from `{run_dir}/scores.json` (inline gate output); build/test/lint were **not** re-run per the skill's "don't re-run" rule.

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:create_book` → `repository.py:create`; test `test_api.py:41` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:list_books` → `repository.py:list_books`; tests in `test_api.py` List class |
| R3 | GET /books ?author= filter | ✓ implemented | `repository.py:list_books` `WHERE fold(author)=?`; `test_api.py:307,325` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:get_book` raises `_book_not_found`; route regex `_BOOK_PATH` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:update_book` → `repository.py:update` (rowcount→404) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:delete_book` → `repository.py:delete` (bool→404/204) |
| R7 | Data stored in SQLite | ✓ implemented | `repository.py:_SCHEMA`, `sqlite3.connect`; not just in-memory |
| R8 | JSON responses + correct status codes | ✓ implemented | `web.py:Response.send` JSON; 201/200/204/400/404/405 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `validation.py:_required_text`; `test_api.py:173` missing field → 400 |
| R10 | GET /health | ✓ implemented | `app.py:health` (pings DB, 200/503); `test_api.py:34` |
| R11 | README.md setup + run instructions | ✓ implemented | `README.md` — routes table, Setup, Run sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 172 test functions across 4 test modules; coverage 0.99 |

Prompt factor (`neutral`): "include tests that demonstrate the implementation meets the requirements" — satisfied (see R12); no methodology prescribed.

## Build & Test

Not re-run — stored scores used per skill Step 2.

```text
scores.json
test_coverage = 0.99   (build + all tests passed; branch coverage on)
defect_rate   = 1.0    (build+test succeeded)
code_quality  = 0.8333
maintainability = 0.9033
idiomatic     = 0.89
```

```text
skip scan: pytest.skip / @pytest.mark.skip / xfail → 0 matches
test functions: 172 (test_api=76, test_server=42, test_repository=30, test_validation=24)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 739 |
| Lines of code (tests) | 1722 |
| Files (excl. __pycache__/.git) | 26 |
| Runtime dependencies | 0 (stdlib only) |
| Dev dependencies | 2 (pytest, pytest-cov) |
| Tests total | 172 |
| Tests effective | 172 |
| Skip ratio | 0% |
| Test coverage | 0.99 |

## Findings

Top items by severity (full list in `findings.jsonl` — all info-level, no critical/high/medium/low):

1. [info] Unicode-aware author filtering beyond spec (`repository.py:35`)
2. [info] Production hardening well beyond the task — body size cap, chunked rejection, threaded server w/ timeouts, HEAD, JSON protocol errors
3. [info] Zero runtime dependencies (stdlib-only WSGI + sqlite3)
4. [info] Coverage 0.99 not 1.0 — one uncovered line, no requirement impact

## Reproduce

```bash
cd "experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=max_language=python_model=claude-sonnet-5-5_prompt=neutral/rep2"
cat scores.json                                              # stored mechanical scores
cat ../../../REQUIREMENTS.json                               # pinned 12-item checklist
grep -rhoE "def test_[a-zA-Z0-9_]+" tests/ | wc -l           # 172 test functions
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/     # 0 skips
find src -name '*.py' | xargs wc -l | tail -1                # 739 source LOC
```
