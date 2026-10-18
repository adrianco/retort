# Evaluation: rest-api-crud · effort=low language=python model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json); no build step (pure stdlib)
- **Lint:** n/a — `code_quality=0.62`, `maintainability=0.93`, `idiomatic=0.60` (scores.json)
- **Architecture:** single-module stdlib app (see below; `run-summary` skill not invokable in this session)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `books_api.py:195` `do_POST` → `store.create` (`:70`); returns 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `books_api.py:185-187` → `store.list` (`:79`) |
| R3 | GET /books ?author= filter | ✓ implemented | `books_api.py:186` reads query; `:83` `LOWER(author)=LOWER(?)`; test `:63` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `books_api.py:188-192`; test `:98` |
| R5 | PUT /books/{id} updates | ✓ implemented | `books_api.py:208` `do_PUT` → `store.update` (`:95`); test `:74` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `books_api.py:224` `do_DELETE` → `store.delete` (`:110`); test `:87` |
| R7 | Data stored in SQLite | ✓ implemented | `books_api.py:40` `sqlite3.connect`; `:46` CREATE TABLE books |
| R8 | JSON + correct status codes | ✓ implemented | `books_api.py:267` `_send_json`; 201/200/204/400/404/405 used throughout |
| R9 | title & author required (400) | ✓ implemented | `books_api.py:141-147` + `ValidationError` → 400 `:202`; test `:103` |
| R10 | GET /health | ✓ implemented | `books_api.py:183-184` returns `{"status":"ok"}`; test `:42` |
| R11 | README with setup/run | ✓ implemented | `README.md` Setup/Run/Test/API sections |
| R12 | ≥3 tests that run | ✓ implemented | 11 test fns (one ×6 parametrized) = 16 cases; `test_coverage=0.91` |

## Build & Test

No compile/build step — pure Python standard library (`http.server`, `sqlite3`).

```text
# scores from scores.json (scorers already ran; not re-run per evaluate-run skill)
test_coverage = 0.91   # tests executed and passed (>0 ⇒ ran; defect_rate=1.0 ⇒ all pass)
defect_rate   = 1.0    # build + test succeeded
```

Tests are integration-style: each spins up the real server on an ephemeral port
(`test_books_api.py:13`) and drives it over HTTP. 0 skips/xfails.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, `books_api.py`) | 322 |
| Lines of code (tests) | 141 |
| Files (excl. build artifacts) | 3 source (books_api.py, test_books_api.py, README.md) |
| Dependencies | 0 runtime (stdlib); pytest for tests |
| Tests total / effective | 16 / 16 |
| Skip ratio | 0% |
| Build duration | n/a (no build) |

## Architecture

Single module `books_api.py`: `BookStore` (SQLite persistence, `threading.Lock`
for thread safety) + `validate_book` (field validation incl. ISBN/year) +
`BooksRequestHandler` (routing via `do_GET/POST/PUT/DELETE`) on a
`ThreadingHTTPServer`. `create_server(port=0)` makes it test-friendly. Clean
separation of storage / validation / transport.

## Findings

Top findings (full list in `findings.jsonl`) — no defects found:

1. [info] Implementation exceeds spec (405 handling, ISBN/year validation, thread-safe store)
2. [info] `?author=` filter is exact case-insensitive match, not substring (reasonable reading of spec)

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=python_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                 # stored mechanical scores (not re-run)
grep -cE "^def test_" test_books_api.py   # test functions
python -m pytest -v             # optional: re-run tests (16 cases)
```
