# Evaluation: rest-api-crud · effort=low model=claude-fable-5-1 prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-fable-5-1, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass — from `test_coverage=0.95`, `defect_rate=1.0` (scores.json; not re-run)
- **Lint:** pass — `code_quality=0.7888` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

Checklist pinned by `rest-api-crud/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:159 create_book`, route `app.py:110`; test `test_create_and_get` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:144 list_books`, route `app.py:109`; test `test_list_and_author_filter` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:147 WHERE author = ? COLLATE NOCASE`; test `test_list_and_author_filter:106` |
| R4 | GET /books/{id} single book (404) | ✓ implemented | `app.py:152 get_book` (404 at `:155`); test `test_not_found_and_method_not_allowed` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:168 update_book` (404 at `:176`); test `test_update`, `test_update_validation_and_missing` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:179 delete_book` (404 at `:183`); test `test_delete` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:59-70 CREATE TABLE books`, `sqlite3.connect` at `:73` |
| R8 | JSON responses + HTTP status codes | ✓ implemented | `STATUS` map `app.py:11-19`, JSON body `app.py:89-93`; 201/200/204/400/404/405 exercised |
| R9 | Input validation: title & author required | ✓ implemented | `app.py:33 validate_book` (400 at `:54`); test `test_create_validation` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:102-104` returns `{"status":"ok"}`; test `test_health` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — setup, env vars, endpoints, examples, test command |
| R12 | ≥3 unit/integration tests | ✓ implemented | 10 tests in `test_app.py`; `test_coverage=0.95` |

No enhancements are counted against the run; robustness beyond spec is noted as `enh-1` (info).

## Build & Test

Not re-run — stored mechanical scores were read from `scores.json` (per skill Step 2):

```text
test_coverage = 0.95    # build succeeded, all tests executed and passed
defect_rate   = 1.0     # build + test success
code_quality  = 0.7888  # lint/quality
maintainability = 1.0
idiomatic     = 0.68
```

Test suite: `python3 -m unittest -v` — 10 test functions, 0 skips, integration
style (real local HTTP server on an ephemeral port + temp SQLite DB).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 196 (`app.py`) + 145 (`test_app.py`) = 341 |
| Files (non-artifact) | 4 (`app.py`, `test_app.py`, `README.md`, `stack.json`) |
| Dependencies | 0 (Python standard library only) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl` (2 items):

1. [low] main() and the generic 500 handler are not exercised by tests (`test_coverage=0.95`)
2. [info] Validation and robustness beyond spec (year/isbn type checks, 405, 1 MiB body cap)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=low_language=python_model=claude-fable-5-1_prompt=neutral/rep1
cat scores.json            # stored mechanical scores (not re-run)
cat ../../../REQUIREMENTS.json   # pinned checklist
grep -cE "def test_" test_app.py # test count
python3 -m unittest -v     # optional: re-run the suite
```
